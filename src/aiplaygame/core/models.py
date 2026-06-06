from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from aiplaygame.core.cards import Rank, sort_cards

ActionKind = Literal["bid", "play", "pass"]
EventType = Literal["deal", "bid", "turn_start", "play", "pass", "decision", "game_over", "error"]


class Action(BaseModel):
    kind: ActionKind
    player: int | None = None
    cards: list[Rank] = Field(default_factory=list)
    bid: int | None = None

    model_config = ConfigDict(frozen=True)

    @classmethod
    def play(cls, player: int, cards: list[Rank]) -> Action:
        return cls(kind="play", player=player, cards=sort_cards(cards))

    @classmethod
    def pass_turn(cls, player: int) -> Action:
        return cls(kind="pass", player=player, cards=[])

    @classmethod
    def bid_turn(cls, player: int, bid: int) -> Action:
        return cls(kind="bid", player=player, bid=bid, cards=[])


class CardFace(BaseModel):
    id: str
    rank: Rank
    suit: str


class DecisionTrace(BaseModel):
    player: int
    selected: Action
    candidates: list[Action]
    win_rate: float
    elapsed_ms: float
    fallback: bool = False
    reason: str = ""
    agent_kind: str = "unknown"
    thought: str = ""
    public_thought: str = ""


class GameState(BaseModel):
    match_id: str
    phase: Literal["dealing", "bidding", "playing", "finished"]
    landlord: int | None = None
    current_player: int = 0
    bottom_cards: list[Rank] = Field(default_factory=list)
    hands: dict[int, list[Rank]] = Field(default_factory=dict)
    hand_counts: dict[int, int] = Field(default_factory=dict)
    last_action: Action | None = None
    last_player: int | None = None
    pass_count: int = 0
    history: list[Action] = Field(default_factory=list)
    played_cards: list[Rank] = Field(default_factory=list)
    card_faces: dict[str, Any] = Field(default_factory=dict)
    remaining_deck_counts: dict[Rank, int] = Field(default_factory=dict)
    winner: int | None = None
    landlord_team_won: bool | None = None


class MatchEvent(BaseModel):
    type: EventType
    match_id: str
    seq: int
    ts: float
    player: int | None = None
    action: Action | None = None
    state: GameState | None = None
    trace: DecisionTrace | None = None
    message: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class LocalMatchRequest(BaseModel):
    players: list[str] = Field(default_factory=lambda: ["ai", "heuristic", "ai"])
    main_player: int = Field(default=0, ge=0, le=2)
    seed: int | None = None
    delay_seconds: float = Field(default=0.75, ge=0.0, le=5.0)
    min_ai_turn_seconds: float = Field(default=5.0, ge=0.0, le=30.0)


class LocalMatchResponse(BaseModel):
    match_id: str
    ws_url: str
    state: GameState
    main_player: int = 0
    player_profiles: dict[int, dict[str, str]] = Field(default_factory=dict)


class HumanActionRequest(BaseModel):
    player: int = Field(ge=0, le=2)
    kind: Literal["play", "pass"]
    cards: list[Rank] = Field(default_factory=list)


class ReplayImportResponse(BaseModel):
    match_id: str
    events: list[MatchEvent]


class RoomPlayerConfig(BaseModel):
    kind: Literal["llm", "douzero", "human", "empty"] = "empty"
    name: str = Field(default="", max_length=40)
    avatar_url: str = Field(default="", max_length=500)
    bio: str = Field(default="", max_length=240)
    model: str = Field(default="", max_length=80)
    api_key: str = Field(default="", max_length=500)
    base_url: str = Field(default="", max_length=500)


class RoomSeat(BaseModel):
    seat: int = Field(ge=0, le=2)
    kind: Literal["llm", "douzero", "human", "empty"]
    label: str = ""
    name: str = ""
    avatar_url: str = ""
    bio: str = ""
    model: str = ""
    base_url: str = ""
    has_api_key: bool = False
    status: Literal["ready", "open", "pending"] = "ready"
    request_id: str | None = None
    display_name: str = ""


class RoomCreateRequest(BaseModel):
    name: str = "直播房间"
    players: list[RoomPlayerConfig] = Field(
        default_factory=lambda: [
            RoomPlayerConfig(kind="llm", name="LLM 玩家", model="gpt-4o-mini"),
            RoomPlayerConfig(kind="douzero", name="DouZero 玩家"),
            RoomPlayerConfig(kind="empty", name="空位"),
        ]
    )
    main_player: int = Field(default=0, ge=0, le=2)
    auto_restart: bool = False
    seed: int | None = None
    delay_seconds: float = Field(default=0.75, ge=0.0, le=5.0)
    min_ai_turn_seconds: float = Field(default=5.0, ge=0.0, le=30.0)


class RoomJoinRequest(BaseModel):
    display_name: str = Field(default="Human Player", min_length=1, max_length=40)


class RoomApproveRequest(BaseModel):
    request_id: str


class RoomStartRequest(BaseModel):
    auto_restart: bool | None = None
    seed: int | None = None


class RoomResponse(BaseModel):
    room_id: str
    name: str
    status: Literal["waiting", "running", "stopped"]
    players: list[RoomSeat]
    main_player: int
    auto_restart: bool
    match_id: str | None = None
    join_url: str
    stream_url: str
    ws_url: str | None = None
