from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from aiplaygame.agents.model import ModelAgent
from aiplaygame.core.cards import normalize_cards, sort_cards
from aiplaygame.core.models import Action, GameState, MatchEvent
from aiplaygame.core.rules import legal_actions


@dataclass
class BotzoneTurn:
    player: int
    hand: list[str]
    hand_counts: dict[int, int]
    last_action: Action | None
    history: list[Action]
    landlord: int | None = None


class BotzoneAdapter:
    """Tolerant adapter around Botzone's generic requests/responses envelope.

    Botzone game payloads are game-specific. This adapter supports a compact
    canonical shape used by the tests and keeps the mapper isolated so the exact
    FightTheLandlord variant can be adjusted without touching the AI.
    """

    def __init__(self) -> None:
        self.agent = ModelAgent()

    def decide_payload(self, payload: dict) -> Action:
        turn = self.parse_turn(payload)
        state = self._state_from_turn(turn)
        trace = self.agent.decide(state, turn.player)
        if trace.selected.kind == "pass" or trace.selected in legal_actions(
            turn.hand, turn.last_action, turn.player
        ):
            return trace.selected
        return legal_actions(turn.hand, turn.last_action, turn.player)[0]

    def format_response(self, action: Action) -> list[str] | dict[str, list[str] | int]:
        if action.kind == "pass":
            return []
        return action.cards

    def parse_turn(self, payload: dict) -> BotzoneTurn:
        requests = payload.get("requests") or []
        responses = payload.get("responses") or []
        latest = requests[-1] if requests else payload
        first = requests[0] if requests else payload

        player = int(latest.get("player", latest.get("position", first.get("player", 0))))
        landlord = latest.get("landlord", first.get("landlord"))
        landlord = int(landlord) if landlord is not None else None

        hand_source = (
            latest.get("hand")
            or latest.get("own")
            or latest.get("cards")
            or first.get("hand")
            or first.get("own")
            or first.get("cards")
            or []
        )
        hand = normalize_cards(hand_source)
        hand_counts = self._parse_hand_counts(latest, first, player, len(hand))

        history = self._parse_history(requests, responses)
        last_action = self._latest_play(history, player)

        return BotzoneTurn(
            player=player,
            hand=hand,
            hand_counts=hand_counts,
            last_action=last_action,
            history=history,
            landlord=landlord,
        )

    def import_replay(self, payload: dict) -> tuple[str, list[MatchEvent]]:
        match_id = uuid4().hex
        turn = self.parse_turn(payload)
        state = self._state_from_turn(turn, match_id=match_id)
        state.history = []
        events = [
            MatchEvent(
                type="deal",
                match_id=match_id,
                seq=1,
                ts=0,
                state=state,
                message="imported Botzone-style replay shell",
            )
        ]
        for index, action in enumerate(turn.history, start=2):
            state.history.append(action)
            events.append(
                MatchEvent(
                    type=action.kind if action.kind in {"play", "pass"} else "play",
                    match_id=match_id,
                    seq=index,
                    ts=index,
                    player=action.player,
                    action=action,
                    state=state,
                )
            )
        return match_id, events

    def _state_from_turn(self, turn: BotzoneTurn, match_id: str | None = None) -> GameState:
        hands = {0: [], 1: [], 2: []}
        hands[turn.player] = sort_cards(turn.hand)
        return GameState(
            match_id=match_id or uuid4().hex,
            phase="playing",
            landlord=turn.landlord,
            current_player=turn.player,
            hands=hands,
            hand_counts=turn.hand_counts,
            last_action=turn.last_action,
            last_player=turn.last_action.player if turn.last_action else None,
            history=turn.history,
        )

    def _parse_hand_counts(
        self,
        latest: dict,
        first: dict,
        player: int,
        own_count: int,
    ) -> dict[int, int]:
        raw = (
            latest.get("handCounts")
            or latest.get("hand_counts")
            or latest.get("cardCounts")
            or latest.get("remainingCounts")
            or first.get("handCounts")
            or first.get("hand_counts")
            or first.get("cardCounts")
            or first.get("remainingCounts")
        )
        counts = {0: 17, 1: 17, 2: 17}
        counts[player] = own_count
        if isinstance(raw, list):
            for seat, count in enumerate(raw[:3]):
                counts[seat] = int(count)
            counts[player] = own_count
        elif isinstance(raw, dict):
            for seat, count in raw.items():
                counts[int(seat)] = int(count)
            counts[player] = own_count
        return counts

    def _parse_history(self, requests: list[dict], responses: list) -> list[Action]:
        history: list[Action] = []
        for request in requests:
            action = self._extract_action(request)
            if action is not None:
                history.append(action)
        for index, response in enumerate(responses):
            action = self._response_to_action(response, index)
            if action is not None:
                history.append(action)
        return history

    def _extract_action(self, item: dict) -> Action | None:
        raw = item.get("lastAction") or item.get("last_action") or item.get("action")
        if raw is None:
            return None
        if isinstance(raw, list):
            player = int(item.get("lastPlayer", item.get("last_player", item.get("player", 0))))
            if not raw:
                return Action.pass_turn(player)
            return Action.play(player, normalize_cards(raw))
        if isinstance(raw, dict):
            player = int(raw.get("player", item.get("player", 0)))
            kind = raw.get("kind") or raw.get("type")
            cards = normalize_cards(raw.get("cards", []))
            if kind == "pass" or not cards:
                return Action.pass_turn(player)
            return Action.play(player, cards)
        return None

    def _response_to_action(self, response: object, index: int) -> Action | None:
        player = index % 3
        if isinstance(response, dict):
            player = int(response.get("player", player))
            cards = response.get("cards", response.get("response", []))
        else:
            cards = response
        if cards is None:
            return None
        if not cards:
            return Action.pass_turn(player)
        if isinstance(cards, list):
            return Action.play(player, normalize_cards(cards))
        return None

    def _latest_play(self, history: list[Action], player: int) -> Action | None:
        active_play: Action | None = None
        passes_after_play = 0
        for action in history:
            if action.kind == "play":
                active_play = action
                passes_after_play = 0
            elif action.kind == "pass" and active_play is not None:
                passes_after_play += 1
                if passes_after_play >= 2:
                    active_play = None
                    passes_after_play = 0
        if active_play is not None and active_play.player != player:
            return active_play
        return None
