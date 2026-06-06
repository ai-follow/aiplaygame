from aiplaygame.agents.llm import LLMAgent
from aiplaygame.agents.model import create_agent
from aiplaygame.agents.spec import PlayerSpec
from aiplaygame.core.models import GameState


def test_player_spec_parses_llm_endpoint():
    spec = PlayerSpec.parse("llm:gpt-4o-mini:http://localhost:9999/v1/chat/completions", 1)
    assert spec.kind == "llm"
    assert spec.model == "gpt-4o-mini"
    assert spec.endpoint == "http://localhost:9999/v1/chat/completions"


def test_llm_agent_without_endpoint_raises_instead_of_policy_fallback():
    state = GameState(
        match_id="test",
        phase="playing",
        landlord=0,
        current_player=1,
        hands={0: [], 1: ["8", "9", "T", "J", "Q"], 2: []},
        hand_counts={0: 12, 1: 5, 2: 8},
        last_action=None,
    )
    try:
        LLMAgent(model="local-test").decide(state, 1)
    except RuntimeError as exc:
        assert "base_url" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("LLM agent must not fall back to local policy without base_url")


def test_create_agent_accepts_llm_spec():
    assert isinstance(create_agent("llm:local-test"), LLMAgent)


def test_llm_agent_requires_api_key_even_when_base_url_is_configured():
    state = GameState(
        match_id="test",
        phase="playing",
        landlord=0,
        current_player=1,
        hands={0: [], 1: ["8", "9", "T", "J", "Q"], 2: []},
        hand_counts={0: 12, 1: 5, 2: 8},
        last_action={"kind": "play", "player": 0, "cards": ["7"], "bid": None},
    )
    try:
        LLMAgent(model="local-test", endpoint="http://localhost:9999/v1").decide(state, 1)
    except RuntimeError as exc:
        assert "api_key" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("LLM agent must not fall back to local policy without api_key")
