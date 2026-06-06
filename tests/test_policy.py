from aiplaygame.agents.model import create_agent
from aiplaygame.core.models import Action, GameState


def test_policy_agent_finishes_when_possible():
    state = GameState(
        match_id="test",
        phase="playing",
        landlord=0,
        current_player=0,
        hands={0: ["3", "3"], 1: [], 2: []},
        hand_counts={0: 2, 1: 5, 2: 5},
        last_action=None,
    )
    trace = create_agent("ai").decide(state, 0)
    assert trace.selected == Action.play(0, ["3", "3"])
    assert not trace.fallback
    assert "policy search" in trace.reason


def test_farmer_policy_passes_to_teammate_holding_trick():
    state = GameState(
        match_id="test",
        phase="playing",
        landlord=0,
        current_player=2,
        hands={0: [], 1: [], 2: ["7", "8", "9", "T", "J", "Q"]},
        hand_counts={0: 10, 1: 2, 2: 6},
        last_action=Action.play(1, ["6"]),
        last_player=1,
    )
    trace = create_agent("ai").decide(state, 2)
    assert trace.selected == Action.pass_turn(2)
