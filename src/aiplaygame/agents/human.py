from __future__ import annotations

import asyncio
import time

from aiplaygame.agents.policy import PolicySearchAgent
from aiplaygame.core.models import Action, DecisionTrace, GameState
from aiplaygame.core.rules import legal_actions


class HumanAgent(PolicySearchAgent):
    name = "human"

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._queue: asyncio.Queue[Action] = asyncio.Queue()

    async def submit_action(self, action: Action) -> None:
        await self._queue.put(action)

    async def decide_async(self, state: GameState, player: int) -> DecisionTrace:
        started = time.perf_counter()
        candidates = legal_actions(state.hands[player], state.last_action, player)
        try:
            action = await asyncio.wait_for(self._queue.get(), timeout=self.timeout_seconds)
            elapsed = (time.perf_counter() - started) * 1000
            return DecisionTrace(
                player=player,
                selected=action,
                candidates=candidates[:24],
                win_rate=0.5,
                elapsed_ms=elapsed,
                fallback=False,
                reason="human submitted action",
                agent_kind="human",
                public_thought="真人玩家手动选择。",
            )
        except TimeoutError:
            trace = super().decide(state, player)
            return trace.model_copy(
                update={
                    "fallback": True,
                    "agent_kind": "human",
                    "reason": "human timeout; policy autoplay fallback",
                    "public_thought": "真人玩家超时，系统使用策略托管。",
                }
            )

    def decide(self, state: GameState, player: int) -> DecisionTrace:
        trace = super().decide(state, player)
        return trace.model_copy(
            update={
                "fallback": True,
                "agent_kind": "human",
                "reason": "human sync fallback; use decide_async for manual play",
                "public_thought": "同步环境无法等待真人输入，系统使用策略托管。",
            }
        )
