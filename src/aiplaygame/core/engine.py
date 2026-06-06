from __future__ import annotations

import asyncio
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from random import Random
from uuid import uuid4

from aiplaygame.agents.base import Agent
from aiplaygame.core.cards import (
    RANK_VALUE,
    RANKS,
    Rank,
    contains_cards,
    remove_cards,
    sort_cards,
)
from aiplaygame.core.models import Action, CardFace, DecisionTrace, GameState, MatchEvent
from aiplaygame.core.rules import can_beat, classify_cards, legal_actions

EventSink = Callable[[MatchEvent], Awaitable[None]]


@dataclass
class LocalMatchRunner:
    agents: list[Agent]
    player_profiles: dict[int, dict[str, str]] = field(default_factory=dict)
    main_player: int = 0
    match_id: str = field(default_factory=lambda: uuid4().hex)
    seed: int | None = None
    delay_seconds: float = 0.75
    min_ai_turn_seconds: float = 5.0
    max_turns: int = 300
    _seq: int = 0
    state: GameState | None = None
    events: list[MatchEvent] = field(default_factory=list)
    _face_hands: dict[int, list[CardFace]] = field(default_factory=dict)
    _bottom_faces: list[CardFace] = field(default_factory=list)
    _played_faces: list[CardFace] = field(default_factory=list)
    _last_action_faces: list[CardFace] = field(default_factory=list)

    async def run(self, sink: EventSink | None = None) -> list[MatchEvent]:
        if len(self.agents) != 3:
            raise ValueError("斗地主 requires exactly three agents")

        self.state = self._deal_state()
        await self._emit("deal", state=self.state, message="dealt initial hands", sink=sink)
        await self._sleep()

        self._assign_landlord()
        assert self.state.landlord is not None
        for player in range(3):
            bid = 1 if player == self.state.landlord else 0
            action = Action.bid_turn(player, bid)
            self.state.history.append(action)
            await self._emit("bid", player=player, action=action, state=self.state, sink=sink)
            await self._sleep()

        self.state.phase = "playing"
        self.state.current_player = self.state.landlord
        self._refresh_counts()
        await self._emit(
            "turn_start",
            player=self.state.current_player,
            state=self.state,
            message="playing phase started",
            sink=sink,
        )
        await self._sleep()

        turns = 0
        while self.state.phase != "finished" and turns < self.max_turns:
            turns += 1
            player = self.state.current_player
            trace = await self._decide_with_fallback(player)
            await self._emit(
                "decision",
                player=player,
                action=trace.selected,
                state=self.state,
                trace=trace,
                sink=sink,
            )
            await self._sleep()

            self._apply_action(trace.selected)
            await self._emit(
                trace.selected.kind if trace.selected.kind in {"play", "pass"} else "play",
                player=player,
                action=trace.selected,
                state=self.state,
                trace=trace,
                sink=sink,
            )
            await self._sleep()

            if self.state.phase == "finished":
                await self._emit(
                    "game_over",
                    player=self.state.winner,
                    state=self.state,
                    message="normal finish",
                    sink=sink,
                )
                break

        if self.state.phase != "finished":
            self.state.phase = "finished"
            self.state.winner = min(self.state.hand_counts, key=self.state.hand_counts.get)
            self.state.landlord_team_won = self.state.winner == self.state.landlord
            await self._emit(
                "game_over",
                player=self.state.winner,
                state=self.state,
                message="max turn limit reached",
                sink=sink,
            )
        return self.events

    def legal_actions_for(self, player: int) -> list[Action]:
        if self.state is None:
            return []
        if self.state.phase != "playing" or self.state.current_player != player:
            return []
        return legal_actions(self.state.hands[player], self.state.last_action, player)

    async def submit_human_action(self, action: Action) -> None:
        if self.state is None:
            raise ValueError("match has not started")
        if action.player is None:
            raise ValueError("action player is required")
        if self.state.current_player != action.player:
            raise ValueError(f"not player {action.player}'s turn")
        if not self._is_legal_action(action.player, action):
            raise ValueError("illegal action")
        agent = self.agents[action.player]
        submit = getattr(agent, "submit_action", None)
        if submit is None:
            raise ValueError(f"player {action.player} is not a human-controlled seat")
        await submit(action)

    def _deal_state(self) -> GameState:
        faces = self._shuffled_faces()
        self._face_hands = {
            0: self._sort_faces(faces[:17]),
            1: self._sort_faces(faces[17:34]),
            2: self._sort_faces(faces[34:51]),
        }
        self._bottom_faces = self._sort_faces(faces[51:])
        self._played_faces = []
        hands = {
            player: [face.rank for face in self._face_hands[player]]
            for player in range(3)
        }
        bottom = [face.rank for face in self._bottom_faces]
        return GameState(
            match_id=self.match_id,
            phase="bidding",
            current_player=0,
            bottom_cards=bottom,
            hands=hands,
            hand_counts={player: len(hand) for player, hand in hands.items()},
            card_faces=self._card_face_state(),
            remaining_deck_counts={rank: 4 for rank in RANKS[:13]} | {"BJ": 1, "RJ": 1},
        )

    def _assign_landlord(self) -> None:
        assert self.state is not None
        landlord = max(range(3), key=lambda player: self._hand_score(self.state.hands[player]))
        self.state.landlord = landlord
        self._face_hands[landlord] = self._sort_faces(
            [*self._face_hands[landlord], *self._bottom_faces]
        )
        self.state.hands[landlord] = sort_cards(
            [*self.state.hands[landlord], *self.state.bottom_cards]
        )
        self.state.current_player = landlord
        self._refresh_counts()

    def _hand_score(self, hand: list[Rank]) -> float:
        counts = Counter(hand)
        score = 0.0
        for rank, count in counts.items():
            score += RANK_VALUE[rank] * count
            if count == 4:
                score += 24
        if counts["BJ"] and counts["RJ"]:
            score += 30
        return score

    async def _decide_with_fallback(self, player: int) -> DecisionTrace:
        assert self.state is not None
        started = time.perf_counter()
        min_turn_seconds = self._min_turn_seconds(player)
        no_fallback = self.player_profiles.get(player, {}).get("kind") == "llm"
        try:
            trace = await self.agents[player].decide_async(self.state.model_copy(deep=True), player)
            if self._is_legal_action(player, trace.selected):
                await self._enforce_min_turn(started, min_turn_seconds)
                elapsed = (time.perf_counter() - started) * 1000
                trace = trace.model_copy(update={"elapsed_ms": elapsed})
                return trace
            reason = f"agent selected illegal action: {trace.selected.model_dump()}"
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            reason = f"agent failed: {exc}"
        if no_fallback:
            raise RuntimeError(reason)

        fallback = self._fallback_action(player)
        await self._enforce_min_turn(started, min_turn_seconds)
        elapsed = (time.perf_counter() - started) * 1000
        return DecisionTrace(
            player=player,
            selected=fallback,
            candidates=legal_actions(self.state.hands[player], self.state.last_action, player)[:24],
            win_rate=0.5,
            elapsed_ms=elapsed,
            fallback=True,
            reason=reason,
        )

    def _min_turn_seconds(self, player: int) -> float:
        profile = self.player_profiles.get(player, {})
        kind = profile.get("kind", "")
        if kind in {"llm", "douzero"}:
            return self.min_ai_turn_seconds
        return 0.0

    async def _enforce_min_turn(self, started: float, min_turn_seconds: float) -> None:
        remaining = min_turn_seconds - (time.perf_counter() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)

    def _fallback_action(self, player: int) -> Action:
        assert self.state is not None
        actions = legal_actions(self.state.hands[player], self.state.last_action, player)
        non_pass = [action for action in actions if action.kind == "play"]
        if non_pass:
            return sorted(non_pass, key=lambda action: (len(action.cards), action.cards))[0]
        return Action.pass_turn(player)

    def _is_legal_action(self, player: int, action: Action) -> bool:
        assert self.state is not None
        if action.player != player:
            return False
        if action.kind == "pass":
            return self.state.last_action is not None and self.state.last_action.player != player
        if action.kind != "play":
            return False
        if not contains_cards(self.state.hands[player], action.cards):
            return False
        if classify_cards(action.cards) is None:
            return False
        previous_cards = None
        if self.state.last_action is not None and self.state.last_action.player != player:
            previous_cards = self.state.last_action.cards
        return can_beat(action.cards, previous_cards)

    def _apply_action(self, action: Action) -> None:
        assert self.state is not None
        player = self.state.current_player
        if action.player != player:
            raise ValueError(f"Expected player {player}, got action for {action.player}")

        if action.kind == "pass":
            self._last_action_faces = []
            self.state.pass_count += 1
            self.state.history.append(action)
            if self.state.pass_count >= 2 and self.state.last_player is not None:
                self.state.current_player = self.state.last_player
                self.state.last_action = None
                self.state.last_player = None
                self.state.pass_count = 0
            else:
                self.state.current_player = (player + 1) % 3
            self._refresh_counts()
            return

        if action.kind != "play":
            raise ValueError(f"Unexpected action in play loop: {action.kind}")

        played_faces = self._take_faces(player, action.cards)
        self._last_action_faces = played_faces
        self.state.hands[player] = remove_cards(self.state.hands[player], action.cards)
        self.state.played_cards.extend(action.cards)
        self._played_faces.extend(played_faces)
        self.state.history.append(action)
        self.state.last_action = action
        self.state.last_player = player
        self.state.pass_count = 0
        self.state.current_player = (player + 1) % 3
        self._refresh_counts()

        if not self.state.hands[player]:
            self.state.phase = "finished"
            self.state.winner = player
            self.state.landlord_team_won = player == self.state.landlord

    def _refresh_counts(self) -> None:
        assert self.state is not None
        self.state.hands = {player: sort_cards(hand) for player, hand in self.state.hands.items()}
        self.state.hand_counts = {player: len(hand) for player, hand in self.state.hands.items()}
        self.state.card_faces = self._card_face_state()
        played = Counter(self.state.played_cards)
        remaining = {rank: (4 if rank not in {"BJ", "RJ"} else 1) - played[rank] for rank in RANKS}
        self.state.remaining_deck_counts = remaining

    def _shuffled_faces(self) -> list[CardFace]:
        suits = ("S", "H", "C", "D")
        faces: list[CardFace] = []
        for rank in RANKS[:13]:
            for suit in suits:
                faces.append(CardFace(id=f"{rank}{suit}", rank=rank, suit=suit))
        faces.append(CardFace(id="BJ", rank="BJ", suit="BJ"))
        faces.append(CardFace(id="RJ", rank="RJ", suit="RJ"))
        rng = Random(self.seed)
        rng.shuffle(faces)
        return faces

    def _sort_faces(self, faces: list[CardFace]) -> list[CardFace]:
        suit_order = {"S": 0, "H": 1, "C": 2, "D": 3, "BJ": 0, "RJ": 0}
        return sorted(faces, key=lambda face: (RANK_VALUE[face.rank], suit_order[face.suit]))

    def _take_faces(self, player: int, cards: list[Rank]) -> list[CardFace]:
        hand = list(self._face_hands[player])
        selected: list[CardFace] = []
        for rank in sort_cards(cards):
            index = next((idx for idx, face in enumerate(hand) if face.rank == rank), -1)
            if index < 0:
                raise ValueError(f"Cannot remove face for rank {rank!r}")
            selected.append(hand.pop(index))
        self._face_hands[player] = self._sort_faces(hand)
        return self._sort_faces(selected)

    def _card_face_state(self) -> dict[str, object]:
        return {
            "hands": {
                str(player): [face.model_dump(mode="json") for face in self._face_hands[player]]
                for player in range(3)
            },
            "bottom_cards": [face.model_dump(mode="json") for face in self._bottom_faces],
            "played_cards": [face.model_dump(mode="json") for face in self._played_faces],
        }

    async def _emit(
        self,
        event_type: str,
        *,
        player: int | None = None,
        action: Action | None = None,
        state: GameState | None = None,
        trace: DecisionTrace | None = None,
        message: str = "",
        sink: EventSink | None = None,
    ) -> None:
        self._seq += 1
        event = MatchEvent(
            type=event_type,  # type: ignore[arg-type]
            match_id=self.match_id,
            seq=self._seq,
            ts=time.time(),
            player=player,
            action=action,
            state=state.model_copy(deep=True) if state is not None else None,
            trace=trace,
            message=message,
            meta={
                "main_player": self.main_player,
                "player_profiles": self.player_profiles,
                "action_faces": [
                    face.model_dump(mode="json")
                    for face in self._last_action_faces
                ]
                if action is not None and event_type == "play"
                else [],
            },
        )
        self.events.append(event)
        if sink is not None:
            await sink(event)

    async def _sleep(self) -> None:
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
