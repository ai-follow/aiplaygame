from aiplaygame.core.evaluation import EvaluationConfig, evaluate_self_play_sync


def test_evaluation_summary_for_small_seeded_batch():
    summary = evaluate_self_play_sync(
        EvaluationConfig(players=["ai", "heuristic", "ai"], matches=5, seed_start=100)
    )
    assert summary["matches"] == 5
    assert sum(summary["winner_by_player"].values()) == 5
    assert summary["avg_turns"] > 0
    assert summary["p95_decision_ms"] >= 0
    assert summary["max_turn_finishes"] == 0
