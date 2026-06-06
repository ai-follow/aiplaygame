# Self-Play Evaluation

Run deterministic evaluation with:

```bash
aiplaygame-eval self-play --players ai,heuristic,ai --matches 1000 --seed-start 0
```

Equivalent runner subcommand:

```bash
aiplaygame-runner eval --players ai,heuristic,ai --matches 1000 --seed-start 0
```

The summary includes:

- `winner_by_player`: first player to empty their hand.
- `first_out_by_kind`: first-out count grouped by agent kind.
- `landlord_side_win_rate` and `farmer_side_win_rate`.
- `avg_turns`, `avg_decision_ms`, and `p95_decision_ms`.
- `fallback_decisions`: engine-level illegal-action or exception fallbacks.
- `max_turn_finishes`: games ended by the safety cap instead of normal play.
- `elo_delta_first_out_ai_vs_heuristic`: rough first-out Elo delta, useful only as a coarse regression signal.

Current 1000-game seeded validation for `ai,heuristic,ai` at seed `0`:

```json
{
  "matches": 1000,
  "winner_by_player": {"0": 330, "1": 315, "2": 355},
  "first_out_by_kind": {"ai": 685, "heuristic": 315},
  "landlord_side_win_rate": 0.621,
  "farmer_side_win_rate": 0.379,
  "avg_turns": 33.31,
  "p95_decision_ms": 4.403,
  "avg_decision_ms": 1.352,
  "fallback_decisions": 0,
  "max_turn_finishes": 0,
  "elo_delta_first_out_ai_vs_heuristic": 135.0
}
```
