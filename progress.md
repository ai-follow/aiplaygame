Original prompt: Implement the AI 斗地主 Botzone + B站直播 MVP plan in the current empty directory.

Progress:
- Initialized project directory structure for Python backend, React frontend, docs, scripts, and tests.
- Added 斗地主 core rules, legal-action generation, heuristic/model fallback agents, local match runner, Botzone adapter, FastAPI/WebSocket service, CLI entrypoints, and React OBS spectator view.
- Python tests, ruff, frontend TypeScript build, and frontend lint pass.
- Playwright browser validation passed at `http://127.0.0.1:5173/?auto=1`; latest screenshot shows the full 720p spectator layout without overlap.
- Added OBS/B站 and Botzone adapter docs.
- Continued implementation: default `ai` now uses fast policy search instead of a simple heuristic fallback; normal local games emit a final `game_over` event.
- Added `aiplaygame-eval self-play` and `aiplaygame-runner eval`; 1000 seeded games passed with p95 decision latency around 4.4ms, zero fallback decisions, and zero max-turn finishes.
- Added Botzone package builder: `aiplaygame-agent package --out dist/botzone-agent.zip`; the zip can be smoke-run directly with `python dist/botzone-agent.zip`.
- Added player specs and LLM agents: `douzero`, `llm:<model>[:endpoint]`, `policy`, `heuristic`, and `human` metadata. LLM agents support OpenAI-compatible endpoints and local reasoning fallback.
- Refactored the spectator UI into a main-perspective commercial-style 斗地主 table: selected main hand visible, two opponent hands hidden as backs, selectable main perspective, top card counter toggle, per-turn timer, and bottom-only main decision/thought panel.
- Added true human controls: async `HumanAgent`, legal-action API, action submit API, and frontend bottom-dock legal action buttons for human main perspective. Manual submit was verified against a live match.
- Added managed room system: home page creates/stops rooms, room APIs support open seats, join requests, admin approval, room start, optional auto-restart, and per-room stream/join URLs.
- Room-created players now include public display metadata: name, optional avatar URL, and optional bio. LLM room players require API key, base URL, and model; API keys are used server-side only and are not returned by APIs.
- Changed LLM player semantics: LLM players call an OpenAI-compatible API directly and no longer use local policy fallback when missing config, failing calls, or illegal responses occur.
- Enforced minimum 5 second turn duration for `llm` and `douzero` AI seats unless inference itself takes longer.
- Refactored live UI for the requested layout: three player panels on the left, oval table in the center with top bottom-cards and center timer, winner overlay on table, and global action history/card counter toggles in the right rail.
- Refined live UI again per user request: removed the left player-introduction rail and moved all player information into the oval table. The table now uses an outer player-info layer, a middle hand layer with only the main perspective face-up, and an inner played-card/timer layer.
- Updated live UI per latest request: the table is now rectangular, history/card-counter toggles are in the top toolbar, the turn timer is a clock badge attached to the active player's hand layer, and visible played actions ignore internal `decision` events.
- Added a backend regression test proving AI minimum turn duration is enforced; latest visual state also showed `elapsed_ms` around 5000ms for DouZero turns.
- Validation passed: `pytest`, `ruff check .`, `npm run build --prefix frontend`, `npm run lint --prefix frontend`, and Playwright screenshots for room manager and room stream at `http://127.0.0.1:5174`.
- Latest Playwright visual verification for the table-layer layout is in `output/web-game-room-tablelayers-live/shot-0.png`.
- Latest Playwright visual verification for the rectangular table/timer layout is in `output/web-game-room-rect-timer/shot-0.png`.
- Updated card rendering to SVG-based card faces/backs in the live frontend, moved hand counts into the hand layer, tightened side-player vertical stacks, and fixed bottom main-hand clipping. Validation passed with `npm run build --prefix frontend`, `npm run lint --prefix frontend`, and Playwright screenshots at `http://127.0.0.1:5175/?auto=1&players=douzero,douzero,douzero` (latest default output: `output/web-game/shot-4.png`).
- Refactored the frontend out of the oversized `App.tsx` into card, shared UI, room, table, constants, and utility modules. Updated live table behavior so finished games reveal all remaining hands, active turn countdowns render inside the played-card zone without P labels or panel chrome, and the winner is shown as a centered banner below the bottom cards. Validation passed with frontend lint/build and Playwright screenshots for running and finished policy games.
- Updated joker card SVG rendering so big/small jokers display as Chinese 大王/小王 style cards instead of BJ/RJ or English JOKER labels. Validation passed with frontend lint/build and Playwright screenshot inspection.

Notes:
- Commercial-client visual automation is intentionally out of scope. The implementation targets local real-time matches and Botzone-style bot submission flows.

TODO:
- Add exact Botzone FightTheLandlord mapping once the target game payload contract is confirmed.
- Replace policy search with a real DouZero/DouZero+ scorer after model weights and runtime constraints are chosen.
- Optional next step: add card-click composition for human play; current UI presents legal action buttons directly.
- Optional next step: persist rooms/player configs in SQLite or another store; current room state is in-memory and resets when the API process restarts.
