from __future__ import annotations

import time
from collections import Counter
from functools import lru_cache
from math import exp

from aiplaygame.agents.base import Agent
from aiplaygame.core.cards import RANK_VALUE, Rank, remove_cards
from aiplaygame.core.models import Action, DecisionTrace, GameState
from aiplaygame.core.rules import classify_cards, generate_plays, legal_actions


class PolicySearchAgent(Agent):
    """Fast deterministic policy used when no pretrained model is configured.

    The scorer is deliberately transparent: it values finishing, reducing the
    estimated number of future turns, preserving bombs unless needed, blocking
    dangerous opponents, and cooperating with the other farmer.
    """

    name = "ai"

    def decide(self, state: GameState, player: int) -> DecisionTrace:
        started = time.perf_counter()
        hand = state.hands[player]
        actions = legal_actions(hand, state.last_action, player)
        scored = [(self._score_action(action, state, player), action) for action in actions]
        selected = max(scored, key=lambda item: item[0])[1]
        elapsed = (time.perf_counter() - started) * 1000
        candidates = [
            action for _, action in sorted(scored, key=lambda item: item[0], reverse=True)[:24]
        ]
        return DecisionTrace(
            player=player,
            selected=selected,
            candidates=candidates,
            win_rate=self._estimate_win_rate(state, player),
            elapsed_ms=elapsed,
            fallback=False,
            reason="fast policy search over legal actions",
        )

    def _score_action(self, action: Action, state: GameState, player: int) -> float:
        hand = state.hands[player]
        landlord = state.landlord
        danger = self._opponent_danger(state, player)
        teammate_holding = self._teammate_is_holding_trick(state, player)
        before_turns = self._estimated_turns(hand)

        if action.kind == "pass":
            score = -4.0
            if teammate_holding:
                score += 18.0
            if danger:
                score -= 16.0
            if state.last_action and state.last_action.player == player:
                score -= 100.0
            return score

        after_hand = remove_cards(hand, action.cards)
        if not after_hand:
            return 10_000.0

        pattern = classify_cards(action.cards)
        if pattern is None:
            return -10_000.0

        if (
            state.last_action
            and state.last_action.kind == "play"
            and not danger
            and not teammate_holding
        ):
            score = 50.0 - RANK_VALUE[pattern.main_rank] * 2.0
            score += (before_turns - self._estimated_turns(after_hand)) * 2.0
            if pattern.type in {"bomb", "rocket"}:
                score -= 100.0
            return score

        after_turns = self._estimated_turns(after_hand)
        score = 0.0
        score += len(action.cards) * 7.5
        score += (before_turns - after_turns) * 16.0
        score -= self._rank_pressure(action) * 0.8

        if pattern.type in {"bomb", "rocket"}:
            score -= 18.0
            if state.last_action and state.last_action.kind == "play" and not danger:
                score -= 60.0
            if danger:
                score += 24.0
            if len(after_hand) <= 2:
                score += 12.0

        if state.last_action and state.last_action.kind == "play":
            if danger:
                score += 10.0
            if teammate_holding:
                score -= 22.0
            if not danger:
                score -= RANK_VALUE[pattern.main_rank] * 1.0
            score += self._control_bonus(action, state, player)
        else:
            score += self._lead_bonus(action, after_hand)

        if landlord is not None and player != landlord:
            next_player = (player + 1) % 3
            if next_player == landlord and state.hand_counts.get(landlord, 99) <= 3:
                score += 8.0

        return score

    def _estimated_turns(self, hand: list[Rank]) -> int:
        return _estimated_turns_cached(tuple(hand))

    def _lead_bonus(self, action: Action, after_hand: list[Rank]) -> float:
        pattern = classify_cards(action.cards)
        if pattern is None:
            return 0.0
        bonus_by_type = {
            "single": -4.0,
            "pair": -1.0,
            "triple": 1.0,
            "triple_single": 5.0,
            "triple_pair": 6.0,
            "straight": 7.0,
            "pair_straight": 8.0,
            "airplane": 9.0,
            "airplane_single": 11.0,
            "airplane_pair": 12.0,
            "bomb": -8.0,
            "rocket": -10.0,
        }
        high_cards_left = sum(1 for card in after_hand if RANK_VALUE[card] >= RANK_VALUE["A"])
        return bonus_by_type[pattern.type] + high_cards_left * 0.8

    def _control_bonus(self, action: Action, state: GameState, player: int) -> float:
        pattern = classify_cards(action.cards)
        if pattern is None:
            return 0.0
        opponents = [seat for seat in range(3) if seat != player]
        lowest_opponent_count = min(state.hand_counts.get(seat, 99) for seat in opponents)
        if lowest_opponent_count <= 2:
            return 14.0 + RANK_VALUE[pattern.main_rank] * 0.7
        return 3.0

    def _opponent_danger(self, state: GameState, player: int) -> bool:
        landlord = state.landlord
        if landlord is None:
            return any(count <= 2 for seat, count in state.hand_counts.items() if seat != player)
        if player == landlord:
            return any(
                state.hand_counts.get(seat, 99) <= 2 for seat in range(3) if seat != landlord
            )
        return state.hand_counts.get(landlord, 99) <= 2

    def _teammate_is_holding_trick(self, state: GameState, player: int) -> bool:
        if state.landlord is None or player == state.landlord:
            return False
        if state.last_action is None or state.last_action.kind != "play":
            return False
        return state.last_action.player not in {None, state.landlord, player}

    def _rank_pressure(self, action: Action) -> float:
        return self._rank_pressure_cards(action.cards)

    def _rank_pressure_cards(self, cards: list[Rank]) -> float:
        if not cards:
            return 0.0
        return sum(RANK_VALUE[card] for card in cards) / len(cards)

    def _estimate_win_rate(self, state: GameState, player: int) -> float:
        own = state.hand_counts.get(player, len(state.hands.get(player, [])))
        opponents = [seat for seat in range(3) if seat != player]
        opponent_best = min(state.hand_counts.get(seat, 20) for seat in opponents)
        played_control = self._played_control_count(state)
        landlord_bonus = 0.14 if state.landlord == player else -0.02
        tempo_bonus = 0.09 if state.current_player == player else 0.0
        raw = (opponent_best - own) * 0.32 + landlord_bonus + tempo_bonus + played_control * 0.025
        return round(1 / (1 + exp(-raw)), 4)

    def _played_control_count(self, state: GameState) -> int:
        counts = Counter(state.played_cards)
        bombs = sum(1 for count in counts.values() if count == 4)
        rocket = int(counts["BJ"] and counts["RJ"])
        return bombs + rocket


@lru_cache(maxsize=50_000)
def _estimated_turns_cached(hand_key: tuple[Rank, ...]) -> int:
    remaining = list(hand_key)
    turns = 0
    while remaining:
        plays = generate_plays(remaining)
        non_bombs = [
            cards
            for cards in plays
            if (pattern := classify_cards(cards)) is not None
            and pattern.type not in {"bomb", "rocket"}
        ]
        pool = non_bombs or plays
        best = max(pool, key=lambda cards: (len(cards), -_rank_pressure_cards(cards)))
        remaining = remove_cards(remaining, best)
        turns += 1
        if turns > 20:
            return turns
    return turns


def _rank_pressure_cards(cards: list[Rank]) -> float:
    if not cards:
        return 0.0
    return sum(RANK_VALUE[card] for card in cards) / len(cards)
