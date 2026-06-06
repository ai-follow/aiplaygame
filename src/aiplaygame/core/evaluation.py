from __future__ import annotations

import asyncio
import math
from collections import Counter
from dataclasses import dataclass
from statistics import mean
from time import perf_counter
from typing import Any

from aiplaygame.agents.model import create_agent
from aiplaygame.core.engine import LocalMatchRunner
from aiplaygame.core.models import MatchEvent


@dataclass(frozen=True)
class EvaluationConfig:
    players: list[str]
    matches: int = 1000
    seed_start: int = 0


async def evaluate_self_play(config: EvaluationConfig) -> dict[str, Any]:
    if len(config.players) != 3:
        raise ValueError("players must contain exactly three agent kinds")
    if config.matches <= 0:
        raise ValueError("matches must be positive")

    started = perf_counter()
    winner_by_player: Counter[int] = Counter()
    first_out_by_kind: Counter[str] = Counter()
    landlord_games_by_kind: Counter[str] = Counter()
    landlord_wins_by_kind: Counter[str] = Counter()
    farmer_side_wins = 0
    landlord_side_wins = 0
    turn_counts: list[int] = []
    decision_latencies: list[float] = []
    fallback_decisions = 0
    max_turn_finishes = 0

    for offset in range(config.matches):
        runner = LocalMatchRunner(
            agents=[create_agent(kind) for kind in config.players],
            seed=config.seed_start + offset,
            delay_seconds=0,
        )
        events = await runner.run()
        state = runner.state
        if state is None or state.winner is None or state.landlord is None:
            raise RuntimeError(f"match {offset} did not finish with a winner")

        winner_by_player[state.winner] += 1
        first_out_by_kind[config.players[state.winner]] += 1
        landlord_kind = config.players[state.landlord]
        landlord_games_by_kind[landlord_kind] += 1
        if state.landlord_team_won:
            landlord_side_wins += 1
            landlord_wins_by_kind[landlord_kind] += 1
        else:
            farmer_side_wins += 1
        if _finished_by_max_turn(events):
            max_turn_finishes += 1

        turn_counts.append(sum(1 for event in events if event.type in {"play", "pass"}))
        for event in events:
            if event.trace is not None:
                decision_latencies.append(event.trace.elapsed_ms)
                if event.trace.fallback:
                    fallback_decisions += 1

    focus = "ai"
    baseline = "heuristic"
    elo_delta = _elo_delta(first_out_by_kind[focus], first_out_by_kind[baseline])
    elapsed_ms = (perf_counter() - started) * 1000

    return {
        "matches": config.matches,
        "players": config.players,
        "seed_start": config.seed_start,
        "winner_by_player": dict(sorted(winner_by_player.items())),
        "first_out_by_kind": dict(sorted(first_out_by_kind.items())),
        "landlord_games_by_kind": dict(sorted(landlord_games_by_kind.items())),
        "landlord_wins_by_kind": dict(sorted(landlord_wins_by_kind.items())),
        "landlord_side_win_rate": round(landlord_side_wins / config.matches, 4),
        "farmer_side_win_rate": round(farmer_side_wins / config.matches, 4),
        "avg_turns": round(mean(turn_counts), 2),
        "p95_decision_ms": round(_percentile(decision_latencies, 0.95), 3),
        "avg_decision_ms": round(mean(decision_latencies), 3),
        "fallback_decisions": fallback_decisions,
        "max_turn_finishes": max_turn_finishes,
        "elo_delta_first_out_ai_vs_heuristic": elo_delta,
        "elapsed_ms": round(elapsed_ms, 1),
    }


def evaluate_self_play_sync(config: EvaluationConfig) -> dict[str, Any]:
    return asyncio.run(evaluate_self_play(config))


def _finished_by_max_turn(events: list[MatchEvent]) -> bool:
    return bool(events and events[-1].type == "game_over" and "max turn" in events[-1].message)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * percentile) - 1))
    return ordered[index]


def _elo_delta(wins: int, losses: int) -> float | None:
    total = wins + losses
    if total == 0:
        return None
    score = min(0.99, max(0.01, wins / total))
    return round(400 * math.log10(score / (1 - score)), 1)
