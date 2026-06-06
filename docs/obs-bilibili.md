# OBS + B站 Livestream

First start the backend and frontend:

```bash
aiplaygame-api
npm run dev --prefix frontend
```

Use the spectator page as an OBS browser source:

```text
http://127.0.0.1:5173/?auto=1&main=0&players=douzero,llm:commercial,llm:local-private
```

Recommended browser-source size:

- 1920 x 1080 for normal livestream output.
- 1280 x 720 for lightweight local testing.

B站 stream server and stream key should be configured in OBS or B站直播工具 only. Do not put stream keys in repository files.

The page supports:

- Auto-start with `?auto=1`.
- Main perspective selection with `main=0`, `main=1`, or `main=2`.
- Player specs with `players=douzero,llm:commercial,llm:local-private`.
- Main perspective privacy: only the selected main player's hand is visible; the other two seats show card backs and counts.
- Manual restart from the top-right button.
- Fullscreen from the top-right button or browser controls.
- A global top card counter that can be toggled on/off.
- `window.render_game_to_text()` for automated visual/state validation.
