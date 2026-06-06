# AI 斗地主 Botzone + B站直播 MVP

This project is a compliant MVP for AI 斗地主 research, local real-time play, Botzone-style bot submission, and OBS/B站 livestream output.

It does not automate commercial game clients or public matchmaking. The supported paths are:

- Local real-time matches rendered in a browser spectator view for OBS capture.
- Botzone-style stdin/stdout bot execution, with game-specific mapping isolated for future adjustment.
- Optional model integration hooks. The default `ai` agent uses a fast policy-search scorer so the MVP runs without bundled third-party weights.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

npm install --prefix frontend

# terminal 1
aiplaygame-api

# terminal 2
npm run dev --prefix frontend
```

Open the Vite URL, usually [http://localhost:5173](http://localhost:5173). The home page manages rooms, player approval, and stream URLs. In OBS, add a browser source pointing at a room stream URL and push to B站 with your own stream key.

Default spectator match:

```text
http://127.0.0.1:5173/?auto=1&main=0&players=douzero,douzero,douzero
```

## CLI

```bash
# Run a local match in the terminal.
aiplaygame-runner local --players ai,heuristic,ai

# Run DouZero adapter vs two LLM players.
aiplaygame-runner local --players douzero,llm:commercial,llm:local-private

# Run seeded self-play evaluation.
aiplaygame-eval self-play --players ai,heuristic,ai --matches 1000

# Botzone-style stdin/stdout entrypoint.
aiplaygame-agent botzone < tests/fixtures/botzone_turn.json

# Build and smoke-run a Botzone submission zip.
aiplaygame-agent package --out dist/botzone-agent.zip
python dist/botzone-agent.zip < tests/fixtures/botzone_turn.json
```

## Backend API

- `POST /api/matches/local` starts a local real-time match.
- `GET /api/matches/{id}` returns match state, events, and replay.
- `WS /ws/matches/{id}` streams `MatchEvent` updates.
- `POST /api/replays/botzone` imports a Botzone-style `requests/responses` payload as a replay shell.
- `GET /api/matches/{id}/legal-actions/{player}` returns legal actions for the current human-controlled player.
- `POST /api/matches/{id}/actions` submits a human action.
- `POST /api/rooms` creates a managed room with player names, optional avatars/bios, and room stream/join links.
- `POST /api/rooms/{id}/join` submits a human join request for the first open seat.
- `POST /api/rooms/{id}/approve` approves a pending human player.
- `POST /api/rooms/{id}/start` starts a full room; `POST /api/rooms/{id}/stop` stops it.

## Player Specs

Each player is configured by a compact string:

- `douzero` or `ai`: current DouZero adapter entry. It keeps the existing DouZero model hook and uses policy search when no model path is configured.
- `llm:<model>:<base_url>`: LLM player using an OpenAI-compatible chat-completions endpoint. Room-created LLM players require API key and base URL.
- `policy`: transparent fast policy-search player.
- `heuristic`: baseline heuristic player.
- `human`: human-controlled seat. The backend waits for submitted legal actions and falls back to policy autoplay on timeout.

LLM players do not use local policy fallback. If the API key/base URL is missing, the endpoint fails, or the model returns an illegal action, the match emits an error instead of silently playing a local action. Room responses never return the stored API key.

## Botzone Package

`aiplaygame-agent package --out dist/botzone-agent.zip` creates a minimal submission zip with `main.py`, `__main__.py`, the bot-facing Python package, a manifest, and `requirements.txt`. It excludes frontend assets, local environments, caches, replays, model files, and livestream credentials.

## Notes on AI Strength

The current code prioritizes correctness, legal actions, state memory, and observability. The default `ai` agent scores legal actions using fast deterministic policy search over the current hand, whole-game history, landlord/farmer role, opponent danger, teammate trick ownership, remaining card memory, and estimated future turns.

To add pretrained DouZero weights, place model assets outside the repository and implement the adapter behind `aiplaygame.agents.model.ModelAgent`.

LLM players are isolated behind `aiplaygame.agents.llm.LLMAgent`. They receive legal actions and public/state information for their seat, then must select a legal action index. `llm` and `douzero` seats wait at least 5 seconds before publishing an action unless inference itself takes longer.

Latest seeded smoke benchmark:

```json
{
  "matches": 1000,
  "players": ["ai", "heuristic", "ai"],
  "first_out_by_kind": {"ai": 685, "heuristic": 315},
  "p95_decision_ms": 4.403,
  "fallback_decisions": 0,
  "max_turn_finishes": 0
}
```

## Live Streaming

Use the room stream page as the OBS browser source. The live UI keeps all players on the left, the oval table in the center, and global panels such as action history and card counter on the right. B站 stream keys and account credentials belong in OBS or local environment files only; do not commit them.
