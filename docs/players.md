# Players and Model Integration

The 斗地主 rules, state, legal-action generation, and match runner live in the core layer. Players are attached through agent implementations, so the same core game can be used by DouZero, LLMs, policy bots, and human controls.

## Supported Player Specs

```text
douzero
llm:gpt-4o-mini:https://api.openai.com
policy
heuristic
human
```

- `douzero` keeps the current DouZero adapter hook. Without `AIPLAYGAME_MODEL_PATH`, it uses fast policy search and labels the trace as DouZero adapter mode.
- `llm:<model>:<base_url>` calls an OpenAI-compatible chat-completions endpoint and asks it to select a legal action index.
- `human` waits for a legal action submitted through the API or frontend. If no action arrives before timeout, it uses policy autoplay so matches do not block forever.

Room-created players also carry public display metadata: `name`, optional `avatar_url`, and optional `bio`. LLM room players additionally require `api_key` and `base_url`; the API key is stored only in memory for the room and is never returned by room APIs.

## Human Controls

When the selected main perspective is a `human` seat, the frontend shows legal action buttons in the bottom dock. The backend APIs are:

```bash
GET /api/matches/{match_id}/legal-actions/{player}
POST /api/matches/{match_id}/actions
```

Submit payload:

```json
{"player": 0, "kind": "play", "cards": ["3", "4", "5", "6", "7"]}
```

Use `{"player": 0, "kind": "pass", "cards": []}` for pass.

## LLM Endpoint Contract

The endpoint should accept a chat-completions-style request:

```json
{
  "model": "local-private",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "{...state and legal_actions...}"}
  ],
  "temperature": 0.1,
  "response_format": {"type": "json_object"}
}
```

It should return JSON content:

```json
{"index": 0, "thought": "short public reasoning"}
```

Only the selected legal action is executed. Invalid, out-of-range, missing, or failed LLM responses do not fall back to local play; the match emits an error event so the operator can fix the player configuration or model response.
