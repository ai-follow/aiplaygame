import asyncio

from aiplaygame.agents.model import create_agent
from aiplaygame.core.engine import LocalMatchRunner


def test_local_match_finishes_with_legal_state():
    runner = LocalMatchRunner(
        agents=[create_agent("heuristic"), create_agent("heuristic"), create_agent("heuristic")],
        seed=7,
        delay_seconds=0,
    )
    events = asyncio.run(runner.run())
    assert events[-1].state is not None
    assert events[-1].type == "game_over"
    assert events[-1].state.phase == "finished"
    assert events[-1].state.winner in {0, 1, 2}
    assert min(events[-1].state.hand_counts.values()) == 0


def test_self_play_does_not_emit_errors_for_many_seeds():
    for seed in range(50):
        runner = LocalMatchRunner(
            agents=[create_agent("ai"), create_agent("heuristic"), create_agent("ai")],
            seed=seed,
            delay_seconds=0,
        )
        events = asyncio.run(runner.run())
        assert events[-1].type == "game_over"
        assert events[-1].state.phase == "finished"
        assert not [event for event in events if event.type == "error"]


def test_ai_minimum_turn_duration_is_enforced():
    runner = LocalMatchRunner(
        agents=[create_agent("douzero"), create_agent("douzero"), create_agent("douzero")],
        player_profiles={
            0: {"kind": "douzero"},
            1: {"kind": "douzero"},
            2: {"kind": "douzero"},
        },
        seed=3,
        delay_seconds=0,
        min_ai_turn_seconds=0.05,
        max_turns=1,
    )
    events = asyncio.run(runner.run())
    decision = next(event for event in events if event.type == "decision")
    assert decision.trace is not None
    assert decision.trace.elapsed_ms >= 45


def test_local_match_emits_physical_card_faces():
    runner = LocalMatchRunner(
        agents=[create_agent("douzero"), create_agent("douzero"), create_agent("douzero")],
        player_profiles={
            0: {"kind": "douzero"},
            1: {"kind": "douzero"},
            2: {"kind": "douzero"},
        },
        seed=5,
        delay_seconds=0,
        min_ai_turn_seconds=0,
        max_turns=1,
    )
    events = asyncio.run(runner.run())
    deal = events[0]
    assert deal.state is not None
    assert deal.state.card_faces["bottom_cards"][0]["suit"] in {"S", "H", "C", "D", "BJ", "RJ"}

    play = next(event for event in events if event.type == "play")
    assert play.action is not None
    assert len(play.meta["action_faces"]) == len(play.action.cards)
    assert play.meta["action_faces"][0]["rank"] in play.action.cards
