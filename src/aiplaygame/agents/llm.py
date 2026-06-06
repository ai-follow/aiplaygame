from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from aiplaygame.agents.base import Agent
from aiplaygame.core.models import Action, DecisionTrace, GameState
from aiplaygame.core.rules import classify_cards, legal_actions


class LLMAgent(Agent):
    name = "llm"

    def __init__(self, model: str = "gpt-4o-mini", endpoint: str = "", api_key: str = "") -> None:
        self.model = model
        base_url = endpoint or os.getenv("AIPLAYGAME_LLM_BASE_URL", "")
        self.endpoint = self._normalize_endpoint(base_url)
        self.api_key = api_key or os.getenv("AIPLAYGAME_LLM_API_KEY", "")

    def decide(self, state: GameState, player: int) -> DecisionTrace:
        started = time.perf_counter()
        hand = state.hands[player]
        actions = legal_actions(hand, state.last_action, player)
        if not self.endpoint:
            raise RuntimeError("LLM base_url is required")
        if not self.api_key:
            raise RuntimeError("LLM api_key is required")
        llm_action, llm_thought = self._decide_with_endpoint(state, player, actions)
        elapsed = (time.perf_counter() - started) * 1000
        return DecisionTrace(
            player=player,
            selected=llm_action,
            candidates=actions[:24],
            win_rate=0.5,
            elapsed_ms=elapsed,
            fallback=False,
            reason=f"llm:{self.model}",
            agent_kind="llm",
            thought=llm_thought,
            public_thought=llm_thought,
        )

    def _normalize_endpoint(self, raw: str) -> str:
        value = raw.strip().rstrip("/")
        if not value:
            return ""
        if value.endswith("/chat/completions"):
            return value
        if value.endswith("/v1"):
            return f"{value}/chat/completions"
        return f"{value}/v1/chat/completions"

    def _decide_with_endpoint(
        self,
        state: GameState,
        player: int,
        actions: list[Action],
    ) -> tuple[Action, str]:
        prompt = self._build_prompt(state, player, actions)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a Dou Dizhu agent. Select exactly one legal action index. "
                        "Return JSON only: {\"index\": number, \"thought\": \"short reason\"}."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}") from exc
        data = json.loads(raw)
        content = self._extract_content(data)
        parsed = json.loads(content)
        index = int(parsed["index"])
        if index < 0 or index >= len(actions):
            raise ValueError(f"LLM selected out-of-range index {index}")
        thought = str(parsed.get("thought", "")).strip()
        return actions[index], thought[:600]

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _extract_content(self, data: dict) -> str:
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        if "message" in data and isinstance(data["message"], dict):
            return data["message"].get("content", "{}")
        if "content" in data:
            return data["content"]
        return json.dumps(data)

    def _build_prompt(self, state: GameState, player: int, actions: list[Action]) -> str:
        public_state = {
            "player": player,
            "landlord": state.landlord,
            "current_player": state.current_player,
            "hand": state.hands[player],
            "hand_counts": state.hand_counts,
            "last_action": state.last_action.model_dump(mode="json") if state.last_action else None,
            "played_cards": state.played_cards,
            "remaining_deck_counts": state.remaining_deck_counts,
            "legal_actions": [
                {
                    "index": index,
                    "kind": action.kind,
                    "cards": action.cards,
                    "pattern": classify_cards(action.cards).type
                    if action.kind == "play" and classify_cards(action.cards)
                    else action.kind,
                }
                for index, action in enumerate(actions[:80])
            ],
        }
        return json.dumps(public_state, ensure_ascii=False)
