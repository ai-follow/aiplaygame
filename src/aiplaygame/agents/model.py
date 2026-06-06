from __future__ import annotations

import os

from aiplaygame.agents.heuristic import ConservativeAgent
from aiplaygame.agents.human import HumanAgent
from aiplaygame.agents.llm import LLMAgent
from aiplaygame.agents.policy import PolicySearchAgent
from aiplaygame.agents.spec import PlayerSpec
from aiplaygame.core.models import DecisionTrace, GameState


class ModelAgent(PolicySearchAgent):
    """Optional pretrained-model adapter.

    The MVP keeps large DouZero-style weights out of git. If AIPLAYGAME_MODEL_PATH is
    configured later, this class is the isolated place to load and score legal actions.
    Until then it uses the transparent policy-search scorer.
    """

    name = "ai"

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or os.getenv("AIPLAYGAME_MODEL_PATH") or ""
        self.model_loaded = False

    def decide(self, state: GameState, player: int) -> DecisionTrace:
        trace = super().decide(state, player)
        if not self.model_loaded:
            return trace.model_copy(
                update={
                    "fallback": False,
                    "reason": "model path not configured; using fast policy search",
                    "agent_kind": "douzero",
                    "public_thought": (
                        "DouZero model path not configured; using policy-search adapter."
                    ),
                }
            )
        return trace


def create_agent(kind: str, api_key: str = "") -> ConservativeAgent | PolicySearchAgent:
    spec = PlayerSpec.parse(kind, seat=0)
    if spec.kind == "douzero":
        return ModelAgent()
    if spec.kind == "llm":
        return LLMAgent(model=spec.model, endpoint=spec.endpoint, api_key=api_key)
    if spec.kind == "policy":
        return PolicySearchAgent()
    if spec.kind == "heuristic":
        return ConservativeAgent()
    if spec.kind == "human":
        return HumanAgent()
    raise ValueError(f"Unknown agent kind: {kind!r}")
