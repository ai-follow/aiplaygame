from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from aiplaygame.agents.model import create_agent
from aiplaygame.agents.spec import PlayerSpec
from aiplaygame.botzone.adapter import BotzoneAdapter
from aiplaygame.core.engine import LocalMatchRunner
from aiplaygame.core.models import (
    Action,
    HumanActionRequest,
    LocalMatchRequest,
    LocalMatchResponse,
    MatchEvent,
    ReplayImportResponse,
    RoomApproveRequest,
    RoomCreateRequest,
    RoomJoinRequest,
    RoomPlayerConfig,
    RoomResponse,
    RoomSeat,
    RoomStartRequest,
)


@dataclass
class MatchRecord:
    runner: LocalMatchRunner | None = None
    events: list[MatchEvent] = field(default_factory=list)
    subscribers: list[asyncio.Queue[MatchEvent]] = field(default_factory=list)
    task: asyncio.Task | None = None

    @property
    def latest_event(self) -> MatchEvent | None:
        return self.events[-1] if self.events else None

    async def publish(self, event: MatchEvent) -> None:
        self.events.append(event)
        stale: list[asyncio.Queue[MatchEvent]] = []
        for queue in self.subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            self.subscribers.remove(queue)


class MatchStore:
    def __init__(self) -> None:
        self.records: dict[str, MatchRecord] = {}

    def get(self, match_id: str) -> MatchRecord:
        try:
            return self.records[match_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="match not found") from exc

    async def create_local(
        self,
        request: LocalMatchRequest,
        api_keys: list[str] | None = None,
        player_profiles: dict[int, dict[str, str]] | None = None,
    ) -> MatchRecord:
        specs = [PlayerSpec.parse(kind, seat=index) for index, kind in enumerate(request.players)]
        keys = [*(api_keys or []), "", "", ""]
        agents = [
            create_agent(kind, api_key=keys[index])
            for index, kind in enumerate(request.players)
        ]
        profiles = {index: spec.profile() for index, spec in enumerate(specs)}
        for index, override in (player_profiles or {}).items():
            profiles[index] = profiles[index] | override
        runner = LocalMatchRunner(
            agents=agents,
            player_profiles=profiles,
            main_player=request.main_player,
            seed=request.seed,
            delay_seconds=request.delay_seconds,
            min_ai_turn_seconds=request.min_ai_turn_seconds,
        )
        record = MatchRecord(runner=runner)
        self.records[runner.match_id] = record

        async def run() -> None:
            try:
                await runner.run(record.publish)
            except Exception as exc:  # pragma: no cover - runtime guard for WebSocket clients
                if runner.state is not None:
                    await record.publish(
                        MatchEvent(
                            type="error",
                            match_id=runner.match_id,
                            seq=len(record.events) + 1,
                            ts=0,
                            state=runner.state,
                            message=str(exc),
                        )
                    )

        record.task = asyncio.create_task(run())
        return record

    async def import_botzone(self, payload: dict) -> tuple[str, MatchRecord]:
        match_id, events = BotzoneAdapter().import_replay(payload)
        record = MatchRecord(events=events)
        self.records[match_id] = record
        return match_id, record

    def stop(self, match_id: str) -> None:
        record = self.get(match_id)
        if record.task is not None and not record.task.done():
            record.task.cancel()


@dataclass
class RoomRecord:
    room_id: str
    name: str
    players: list[RoomSeat]
    agent_specs: list[str]
    agent_api_keys: list[str]
    main_player: int = 0
    auto_restart: bool = False
    status: str = "waiting"
    match_id: str | None = None
    delay_seconds: float = 0.75
    min_ai_turn_seconds: float = 5.0


class RoomStore:
    def __init__(self, match_store: MatchStore) -> None:
        self.rooms: dict[str, RoomRecord] = {}
        self.match_store = match_store

    def get(self, room_id: str) -> RoomRecord:
        try:
            return self.rooms[room_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="room not found") from exc

    def list(self) -> list[RoomRecord]:
        return list(self.rooms.values())

    def create(self, request: RoomCreateRequest) -> RoomRecord:
        if len(request.players) != 3:
            raise HTTPException(status_code=400, detail="players must contain exactly 3 seats")
        room_id = uuid4().hex[:10]
        seats: list[RoomSeat] = []
        agent_specs: list[str] = []
        agent_api_keys: list[str] = []
        for index, config in enumerate(request.players):
            seat, agent_spec, api_key = self._seat_from_config(index, config)
            seats.append(seat)
            agent_specs.append(agent_spec)
            agent_api_keys.append(api_key)
        room = RoomRecord(
            room_id=room_id,
            name=request.name.strip() or "直播房间",
            players=seats,
            agent_specs=agent_specs,
            agent_api_keys=agent_api_keys,
            main_player=request.main_player,
            auto_restart=request.auto_restart,
            delay_seconds=request.delay_seconds,
            min_ai_turn_seconds=request.min_ai_turn_seconds,
        )
        self.rooms[room_id] = room
        return room

    def join(self, room_id: str, request: RoomJoinRequest) -> RoomRecord:
        room = self.get(room_id)
        if room.status != "waiting":
            raise HTTPException(status_code=400, detail="room is not waiting for players")
        for seat in room.players:
            if seat.status == "open":
                seat.status = "pending"
                seat.request_id = uuid4().hex[:10]
                seat.display_name = request.display_name.strip() or "Human Player"
                seat.label = seat.display_name
                seat.name = seat.display_name
                return room
        raise HTTPException(status_code=400, detail="no open seat")

    def approve(self, room_id: str, request: RoomApproveRequest) -> RoomRecord:
        room = self.get(room_id)
        for seat in room.players:
            if seat.status == "pending" and seat.request_id == request.request_id:
                seat.kind = "human"
                seat.status = "ready"
                seat.request_id = None
                seat.label = seat.display_name or f"Human Seat {seat.seat}"
                room.agent_specs[seat.seat] = "human"
                room.agent_api_keys[seat.seat] = ""
                return room
        raise HTTPException(status_code=404, detail="pending request not found")

    async def start(self, room_id: str, request: RoomStartRequest | None = None) -> RoomRecord:
        room = self.get(room_id)
        if request and request.auto_restart is not None:
            room.auto_restart = request.auto_restart
        if any(seat.status != "ready" or not room.agent_specs[seat.seat] for seat in room.players):
            raise HTTPException(status_code=400, detail="all seats must be ready before start")
        if room.match_id:
            try:
                self.match_store.stop(room.match_id)
            except HTTPException:
                pass
        local_request = LocalMatchRequest(
            players=room.agent_specs,
            main_player=room.main_player,
            seed=request.seed if request else None,
            delay_seconds=room.delay_seconds,
            min_ai_turn_seconds=room.min_ai_turn_seconds,
        )
        record = await self.match_store.create_local(
            local_request,
            api_keys=room.agent_api_keys,
            player_profiles=self._player_profiles(room),
        )
        assert record.runner is not None
        while record.runner.state is None:
            await asyncio.sleep(0.01)
        room.status = "running"
        room.match_id = record.runner.match_id
        self._schedule_restart(room.room_id, record)
        return room

    def stop(self, room_id: str) -> RoomRecord:
        room = self.get(room_id)
        if room.match_id:
            try:
                self.match_store.stop(room.match_id)
            except HTTPException:
                pass
        room.status = "stopped"
        return room

    def _schedule_restart(self, room_id: str, record: MatchRecord) -> None:
        async def watch() -> None:
            if record.task is None:
                return
            try:
                await record.task
            except asyncio.CancelledError:
                return
            room = self.rooms.get(room_id)
            if room and room.status == "running" and room.auto_restart:
                await asyncio.sleep(1.2)
                await self.start(room_id, RoomStartRequest(auto_restart=True))

        asyncio.create_task(watch())

    def _seat_from_config(self, seat: int, config: RoomPlayerConfig) -> tuple[RoomSeat, str, str]:
        name = config.name.strip()
        if config.kind == "empty":
            return (
                RoomSeat(
                    seat=seat,
                    kind="empty",
                    label=name or f"空位 P{seat}",
                    name=name or f"空位 P{seat}",
                    avatar_url=config.avatar_url.strip(),
                    bio=config.bio.strip(),
                    status="open",
                ),
                "",
                "",
            )
        if config.kind == "llm":
            model = config.model.strip() or "gpt-4o-mini"
            base_url = config.base_url.strip().rstrip("/")
            api_key = config.api_key.strip()
            if not base_url:
                raise HTTPException(status_code=400, detail=f"P{seat} LLM player requires base_url")
            if not api_key:
                raise HTTPException(status_code=400, detail=f"P{seat} LLM player requires api_key")
            return (
                RoomSeat(
                    seat=seat,
                    kind="llm",
                    label=name or f"LLM {model}",
                    name=name or f"LLM {model}",
                    avatar_url=config.avatar_url.strip(),
                    bio=config.bio.strip(),
                    model=model,
                    base_url=base_url,
                    has_api_key=True,
                    status="ready",
                ),
                f"llm:{model}:{base_url}",
                api_key,
            )
        if config.kind == "douzero":
            return (
                RoomSeat(
                    seat=seat,
                    kind="douzero",
                    label=name or f"DouZero Seat {seat}",
                    name=name or f"DouZero Seat {seat}",
                    avatar_url=config.avatar_url.strip(),
                    bio=config.bio.strip(),
                    model="douzero",
                    status="ready",
                ),
                "douzero",
                "",
            )
        if config.kind == "human":
            return (
                RoomSeat(
                    seat=seat,
                    kind="human",
                    label=name or f"Human Seat {seat}",
                    name=name or f"Human Seat {seat}",
                    avatar_url=config.avatar_url.strip(),
                    bio=config.bio.strip(),
                    model="human",
                    status="ready",
                ),
                "human",
                "",
            )
        raise HTTPException(status_code=400, detail=f"Unknown player kind: {config.kind}")

    def _player_profiles(self, room: RoomRecord) -> dict[int, dict[str, str]]:
        profiles: dict[int, dict[str, str]] = {}
        for seat in room.players:
            profiles[seat.seat] = {
                "kind": seat.kind,
                "label": seat.label,
                "name": seat.name,
                "avatar_url": seat.avatar_url,
                "bio": seat.bio,
                "model": seat.model,
                "endpoint": seat.base_url,
            }
        return profiles


store = MatchStore()
rooms = RoomStore(store)
app = FastAPI(title="AI 斗地主 Play Game", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/matches/local", response_model=LocalMatchResponse)
async def create_local_match(request: LocalMatchRequest) -> LocalMatchResponse:
    if len(request.players) != 3:
        raise HTTPException(status_code=400, detail="players must contain exactly 3 agent kinds")
    record = await store.create_local(request)
    assert record.runner is not None
    while record.runner.state is None:
        await asyncio.sleep(0.01)
    host = os.getenv("AIPLAYGAME_PUBLIC_HOST", "localhost:8000")
    return LocalMatchResponse(
        match_id=record.runner.match_id,
        ws_url=f"ws://{host}/ws/matches/{record.runner.match_id}",
        state=record.runner.state,
        main_player=record.runner.main_player,
        player_profiles=record.runner.player_profiles,
    )


@app.get("/api/rooms", response_model=list[RoomResponse])
async def list_rooms() -> list[RoomResponse]:
    return [room_response(room) for room in rooms.list()]


@app.post("/api/rooms", response_model=RoomResponse)
async def create_room(request: RoomCreateRequest) -> RoomResponse:
    return room_response(rooms.create(request))


@app.get("/api/rooms/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str) -> RoomResponse:
    return room_response(rooms.get(room_id))


@app.post("/api/rooms/{room_id}/join", response_model=RoomResponse)
async def join_room(room_id: str, request: RoomJoinRequest) -> RoomResponse:
    return room_response(rooms.join(room_id, request))


@app.post("/api/rooms/{room_id}/approve", response_model=RoomResponse)
async def approve_room_join(room_id: str, request: RoomApproveRequest) -> RoomResponse:
    return room_response(rooms.approve(room_id, request))


@app.post("/api/rooms/{room_id}/start", response_model=RoomResponse)
async def start_room(room_id: str, request: RoomStartRequest) -> RoomResponse:
    return room_response(await rooms.start(room_id, request))


@app.post("/api/rooms/{room_id}/stop", response_model=RoomResponse)
async def stop_room(room_id: str) -> RoomResponse:
    return room_response(rooms.stop(room_id))


@app.get("/api/matches/{match_id}")
async def get_match(match_id: str) -> dict:
    record = store.get(match_id)
    state = record.latest_event.state if record.latest_event and record.latest_event.state else None
    return {
        "match_id": match_id,
        "state": state.model_dump(mode="json") if state is not None else None,
        "events": [event.model_dump(mode="json") for event in record.events],
        "running": record.task is not None and not record.task.done(),
    }


@app.get("/api/matches/{match_id}/legal-actions/{player}")
async def get_legal_actions(match_id: str, player: int) -> dict:
    record = store.get(match_id)
    if record.runner is None:
        raise HTTPException(status_code=400, detail="match is not interactive")
    actions = record.runner.legal_actions_for(player)
    state = record.runner.state
    return {
        "match_id": match_id,
        "player": player,
        "current_player": state.current_player if state else None,
        "actions": [action.model_dump(mode="json") for action in actions],
    }


@app.post("/api/matches/{match_id}/actions")
async def submit_human_action(match_id: str, request: HumanActionRequest) -> dict[str, str]:
    record = store.get(match_id)
    if record.runner is None:
        raise HTTPException(status_code=400, detail="match is not interactive")
    action = (
        Action.pass_turn(request.player)
        if request.kind == "pass"
        else Action.play(request.player, request.cards)
    )
    try:
        await record.runner.submit_human_action(action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "accepted"}


@app.post("/api/replays/botzone", response_model=ReplayImportResponse)
async def import_botzone_replay(payload: dict) -> ReplayImportResponse:
    match_id, record = await store.import_botzone(payload)
    return ReplayImportResponse(match_id=match_id, events=record.events)


@app.websocket("/ws/matches/{match_id}")
async def stream_match(websocket: WebSocket, match_id: str) -> None:
    await websocket.accept()
    record = store.get(match_id)
    for event in record.events:
        await websocket.send_json(event.model_dump(mode="json"))

    queue: asyncio.Queue[MatchEvent] = asyncio.Queue(maxsize=128)
    record.subscribers.append(queue)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event.model_dump(mode="json"))
            if event.type in {"game_over", "error"}:
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        if queue in record.subscribers:
            record.subscribers.remove(queue)


def room_response(room: RoomRecord) -> RoomResponse:
    frontend_host = os.getenv("AIPLAYGAME_PUBLIC_FRONTEND", "http://localhost:5173")
    ws_url = f"/ws/matches/{room.match_id}" if room.match_id else None
    return RoomResponse(
        room_id=room.room_id,
        name=room.name,
        status=room.status,  # type: ignore[arg-type]
        players=room.players,
        main_player=room.main_player,
        auto_restart=room.auto_restart,
        match_id=room.match_id,
        join_url=f"{frontend_host}/?join={room.room_id}",
        stream_url=f"{frontend_host}/?room={room.room_id}&view=stream",
        ws_url=ws_url,
    )
