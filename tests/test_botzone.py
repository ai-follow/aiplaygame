import json
from pathlib import Path

from aiplaygame.botzone.adapter import BotzoneAdapter
from aiplaygame.core.rules import can_beat, classify_cards


def test_botzone_fixture_outputs_legal_action():
    payload = json.loads(Path("tests/fixtures/botzone_turn.json").read_text())
    adapter = BotzoneAdapter()
    action = adapter.decide_payload(payload)
    assert action.kind in {"play", "pass"}
    if action.kind == "play":
        assert classify_cards(action.cards) is not None
        assert can_beat(action.cards, ["7"])
