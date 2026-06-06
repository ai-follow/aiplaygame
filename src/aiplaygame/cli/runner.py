from __future__ import annotations

import argparse
import asyncio
import json

from aiplaygame.agents.model import create_agent
from aiplaygame.core.engine import LocalMatchRunner
from aiplaygame.core.evaluation import EvaluationConfig, evaluate_self_play_sync
from aiplaygame.core.models import MatchEvent


async def _run_local(players: list[str], seed: int | None, delay_seconds: float) -> None:
    runner = LocalMatchRunner(
        agents=[create_agent(player) for player in players],
        seed=seed,
        delay_seconds=delay_seconds,
    )

    async def print_event(event: MatchEvent) -> None:
        compact = {
            "seq": event.seq,
            "type": event.type,
            "player": event.player,
            "action": event.action.model_dump(mode="json") if event.action else None,
            "winner": event.state.winner if event.state else None,
        }
        print(json.dumps(compact, ensure_ascii=False))

    await runner.run(print_event)


def main() -> None:
    parser = argparse.ArgumentParser(prog="aiplaygame-runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    local = subparsers.add_parser("local", help="Run a local 斗地主 match")
    local.add_argument("--players", default="ai,heuristic,ai")
    local.add_argument("--seed", type=int, default=None)
    local.add_argument("--delay-seconds", type=float, default=0.0)
    evaluate = subparsers.add_parser("eval", help="Run seeded self-play evaluation")
    evaluate.add_argument("--players", default="ai,heuristic,ai")
    evaluate.add_argument("--matches", type=int, default=1000)
    evaluate.add_argument("--seed-start", type=int, default=0)
    args = parser.parse_args()

    if args.command == "local":
        players = [item.strip() for item in args.players.split(",") if item.strip()]
        if len(players) != 3:
            raise SystemExit("--players must contain exactly three comma-separated agent kinds")
        asyncio.run(_run_local(players, args.seed, args.delay_seconds))
    elif args.command == "eval":
        players = [item.strip() for item in args.players.split(",") if item.strip()]
        summary = evaluate_self_play_sync(
            EvaluationConfig(players=players, matches=args.matches, seed_start=args.seed_start)
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
