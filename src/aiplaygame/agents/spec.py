from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerSpec:
    raw: str
    kind: str
    label: str
    model: str = ""
    endpoint: str = ""

    @classmethod
    def parse(cls, raw: str, seat: int) -> PlayerSpec:
        token = raw.strip()
        normalized = token.lower()
        if normalized.startswith("llm"):
            parts = token.split(":", 2)
            model = parts[1] if len(parts) >= 2 and parts[1] else "local-llm"
            endpoint = parts[2] if len(parts) >= 3 else ""
            return cls(raw=raw, kind="llm", label=f"LLM {model}", model=model, endpoint=endpoint)
        if normalized in {"ai", "model", "douzero"}:
            return cls(raw=raw, kind="douzero", label=f"DouZero Seat {seat}", model="douzero")
        if normalized in {"policy", "search"}:
            return cls(raw=raw, kind="policy", label=f"Policy Seat {seat}", model="policy")
        if normalized in {"heuristic", "baseline"}:
            return cls(raw=raw, kind="heuristic", label=f"Heuristic Seat {seat}", model="heuristic")
        if normalized in {"human", "person", "真人"}:
            return cls(raw=raw, kind="human", label=f"Human Seat {seat}", model="human")
        raise ValueError(f"Unknown player spec: {raw!r}")

    def profile(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "label": self.label,
            "model": self.model,
            "endpoint": self.endpoint,
        }
