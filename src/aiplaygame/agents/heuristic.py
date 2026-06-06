from __future__ import annotations

import time
from math import exp

from aiplaygame.agents.base import Agent
from aiplaygame.core.cards import RANK_VALUE
from aiplaygame.core.models import Action, DecisionTrace, GameState
from aiplaygame.core.rules import classify_cards, legal_actions


class HeuristicAgent(Agent):
    name = "heuristic"

    def decide(self, state: GameState, player: int) -> DecisionTrace:
        started = time.perf_counter()
        hand = state.hands[player]
        actions = legal_actions(hand, state.last_action, player)
        selected = self._select_action(actions, hand, state)
        elapsed = (time.perf_counter() - started) * 1000
        return DecisionTrace(
            player=player,
            selected=selected,
            candidates=actions[:24],
            win_rate=self._estimate_win_rate(state, player),
            elapsed_ms=elapsed,
            fallback=False,
            reason="lowest-risk legal heuristic",
        )

    def _select_action(self, actions: list[Action], hand: list[str], state: GameState) -> Action:
        playable = [action for action in actions if action.kind == "play"]
        finishing = [action for action in playable if len(action.cards) == len(hand)]
        if finishing:
            return sorted(finishing, key=self._action_cost)[0]

        if state.last_action is not None and state.last_action.kind == "play":
            same_type = []
            bombs = []
            for action in playable:
                pattern = classify_cards(action.cards)
                if pattern is None:
                    continue
                if pattern.type in {"bomb", "rocket"}:
                    bombs.append(action)
                else:
                    same_type.append(action)
            if same_type:
                return sorted(same_type, key=self._action_cost)[0]
            pass_action = next((action for action in actions if action.kind == "pass"), None)
            if pass_action is not None:
                return pass_action
            if bombs:
                return sorted(bombs, key=self._action_cost)[0]

        non_bombs = [
            action
            for action in playable
            if (pattern := classify_cards(action.cards)) is not None
            and pattern.type not in {"bomb", "rocket"}
        ]
        if non_bombs:
            return sorted(non_bombs, key=self._lead_cost)[0]
        return sorted(playable, key=self._action_cost)[0]

    def _lead_cost(self, action: Action) -> tuple[int, int, int]:
        pattern = classify_cards(action.cards)
        assert pattern is not None
        # Prefer shedding more cards when leading, while keeping bombs as a last resort.
        return (
            1 if pattern.type in {"bomb", "rocket"} else 0,
            -len(action.cards),
            RANK_VALUE[pattern.main_rank],
        )

    def _action_cost(self, action: Action) -> tuple[int, int, int]:
        pattern = classify_cards(action.cards)
        if pattern is None:
            return (99, 99, 99)
        return (
            1 if pattern.type in {"bomb", "rocket"} else 0,
            len(action.cards),
            RANK_VALUE[pattern.main_rank],
        )

    def _estimate_win_rate(self, state: GameState, player: int) -> float:
        own = state.hand_counts.get(player, len(state.hands.get(player, [])))
        opponent_best = min(
            count for seat, count in state.hand_counts.items() if seat != player
        )
        landlord_bonus = 0.15 if state.landlord == player else -0.03
        tempo_bonus = 0.08 if state.current_player == player else 0.0
        raw = (opponent_best - own) * 0.35 + landlord_bonus + tempo_bonus
        return round(1 / (1 + exp(-raw)), 4)


class ConservativeAgent(HeuristicAgent):
    name = "ai"
