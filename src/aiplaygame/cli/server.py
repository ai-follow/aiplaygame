from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("AIPLAYGAME_HOST", "127.0.0.1")
    port = int(os.getenv("AIPLAYGAME_PORT", "8000"))
    uvicorn.run("aiplaygame.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
