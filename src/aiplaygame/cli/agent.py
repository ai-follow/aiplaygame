from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aiplaygame.botzone.adapter import BotzoneAdapter
from aiplaygame.botzone.package import build_botzone_package


def main() -> None:
    parser = argparse.ArgumentParser(prog="aiplaygame-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "botzone",
        help="Read Botzone-style JSON from stdin and print action JSON",
    )
    package = subparsers.add_parser("package", help="Build Botzone submission zip")
    package.add_argument("--out", default="dist/botzone-agent.zip")
    args = parser.parse_args()

    if args.command == "botzone":
        payload = json.load(sys.stdin)
        adapter = BotzoneAdapter()
        action = adapter.decide_payload(payload)
        print(json.dumps(adapter.format_response(action), ensure_ascii=False))
    elif args.command == "package":
        result = build_botzone_package(Path(args.out))
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
