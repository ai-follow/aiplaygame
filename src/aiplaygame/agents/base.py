from __future__ import annotations

from abc import ABC, abstractmethod

from aiplaygame.core.models import DecisionTrace, GameState


class Agent(ABC):
    name = "agent"

    @abstractmethod
    def decide(self, state: GameState, player: int) -> DecisionTrace:
        raise NotImplementedError

    async def decide_async(self, state: GameState, player: int) -> DecisionTrace:
        return self.decide(state, player)
