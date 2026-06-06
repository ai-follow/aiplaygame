#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from aiplaygame.botzone.package import build_botzone_package


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Botzone submission zip")
    parser.add_argument("--out", default="dist/botzone-agent.zip")
    args = parser.parse_args()
    result = build_botzone_package(Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
