from __future__ import annotations

import argparse
import json

from aiplaygame.core.evaluation import EvaluationConfig, evaluate_self_play_sync


def main() -> None:
    parser = argparse.ArgumentParser(prog="aiplaygame-eval")
    subparsers = parser.add_subparsers(dest="command", required=True)
    self_play = subparsers.add_parser("self-play", help="Run seeded self-play evaluation")
    self_play.add_argument("--players", default="ai,heuristic,ai")
    self_play.add_argument("--matches", type=int, default=1000)
    self_play.add_argument("--seed-start", type=int, default=0)
    args = parser.parse_args()

    if args.command == "self-play":
        players = [item.strip() for item in args.players.split(",") if item.strip()]
        summary = evaluate_self_play_sync(
            EvaluationConfig(players=players, matches=args.matches, seed_start=args.seed_start)
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
