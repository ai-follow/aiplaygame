# Botzone Adapter

`aiplaygame-agent botzone` reads one JSON document from stdin and prints one JSON response to stdout.

The generic envelope is:

```json
{
  "requests": [
    {
      "player": 0,
      "landlord": 0,
      "hand": ["3", "4", "5"],
      "lastAction": { "player": 2, "kind": "play", "cards": ["3"] }
    }
  ],
  "responses": []
}
```

The current output is a card-rank array, or `[]` for pass:

```json
["4"]
```

The exact Botzone FightTheLandlord payload can vary by game version. Keep variant-specific key conversion inside `aiplaygame.botzone.adapter.BotzoneAdapter`; the AI and rules should continue to operate on project ranks: `3 4 5 6 7 8 9 T J Q K A 2 BJ RJ`.

Submission packages must not include stream keys, commercial-client credentials, or network-only model dependencies.

## Build a Submission Zip

```bash
aiplaygame-agent package --out dist/botzone-agent.zip
python dist/botzone-agent.zip < tests/fixtures/botzone_turn.json
```

The package contains:

- `main.py` and `__main__.py`.
- `aiplaygame/agents`, `aiplaygame/botzone`, and the minimal `aiplaygame/core` modules needed for stdin/stdout decisions.
- `BOTZONE_PACKAGE.json` manifest.
- `requirements.txt` with runtime Python dependencies.

The package excludes frontend assets, local virtualenvs, caches, replay output, model folders, and livestream credentials.
