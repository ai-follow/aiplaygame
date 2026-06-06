import {
  AlarmClock,
  Bot,
  BrainCircuit,
  Check,
  Copy,
  Crown,
  Eye,
  EyeOff,
  Maximize2,
  Play,
  RotateCcw,
  Square,
  UserRound,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type {
  Action,
  CardFace,
  DecisionTrace,
  GameState,
  LocalMatchResponse,
  MatchEvent,
  PlayerProfile,
  RoomPlayerConfig,
  RoomResponse,
  RoomSeat
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const RANKS = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A', '2', 'BJ', 'RJ'];
const CARD_SUITS = ['S', 'H', 'C', 'D'] as const;
const CARD_SVG_DECK = buildCardSvgDeck();
const DEFAULT_PLAYERS: RoomPlayerConfig[] = [
  {
    kind: 'llm',
    name: 'LLM 一号',
    avatar_url: '',
    bio: '大模型直接根据牌局状态选择出牌。',
    model: 'gpt-4o-mini',
    api_key: '',
    base_url: 'https://api.openai.com'
  },
  {
    kind: 'douzero',
    name: 'DouZero 一号',
    avatar_url: '',
    bio: '强化学习策略玩家。',
    model: '',
    api_key: '',
    base_url: ''
  },
  {
    kind: 'empty',
    name: '真人空位',
    avatar_url: '',
    bio: '等待玩家通过邀请链接加入。',
    model: '',
    api_key: '',
    base_url: ''
  }
];
const TURN_SECONDS = 30;

type PlayedDisplay = {
  action: Action;
  faces: CardFace[];
};

type CardSvgSpec = {
  id: string;
  rank: string;
  suit: string;
};

declare global {
  interface Window {
    render_game_to_text?: () => string;
    advanceTime?: (ms: number) => void;
    __aiplaygame_auto_started?: boolean;
  }
}

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const joinRoomId = params.get('join');
  const roomId = params.get('room');
  const view = params.get('view');
  const auto = params.get('auto') === '1';

  if (joinRoomId) {
    return <JoinRoomView roomId={joinRoomId} />;
  }
  if (roomId && view === 'stream') {
    return <StreamView roomId={roomId} />;
  }
  if (auto) {
    return <StandaloneAutoView />;
  }
  return <RoomManager />;
}

function RoomManager() {
  const [rooms, setRooms] = useState<RoomResponse[]>([]);
  const [name, setName] = useState('AI 斗地主直播房');
  const [players, setPlayers] = useState(DEFAULT_PLAYERS);
  const [mainPlayer, setMainPlayer] = useState(0);
  const [autoRestart, setAutoRestart] = useState(false);
  const [error, setError] = useState('');

  const loadRooms = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/rooms`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    setRooms((await response.json()) as RoomResponse[]);
  }, []);

  useEffect(() => {
    void loadRooms().catch((err) => setError(err instanceof Error ? err.message : String(err)));
    const interval = window.setInterval(
      () => void loadRooms().catch((err) => setError(err instanceof Error ? err.message : String(err))),
      2500
    );
    return () => window.clearInterval(interval);
  }, [loadRooms]);

  const createRoom = useCallback(async () => {
    setError('');
    const response = await fetch(`${API_BASE}/api/rooms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        players,
        main_player: mainPlayer,
        auto_restart: autoRestart,
        min_ai_turn_seconds: 5
      })
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail || `HTTP ${response.status}`);
      return;
    }
    await loadRooms();
  }, [autoRestart, loadRooms, mainPlayer, name, players]);

  const approve = useCallback(
    async (room: RoomResponse, seat: RoomSeat) => {
      if (!seat.request_id) {
        return;
      }
      await fetch(`${API_BASE}/api/rooms/${room.room_id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: seat.request_id })
      });
      await loadRooms();
    },
    [loadRooms]
  );

  const startRoom = useCallback(
    async (room: RoomResponse) => {
      const response = await fetch(`${API_BASE}/api/rooms/${room.room_id}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_restart: room.auto_restart })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        setError(body.detail || `HTTP ${response.status}`);
      }
      await loadRooms();
    },
    [loadRooms]
  );

  const stopRoom = useCallback(
    async (room: RoomResponse) => {
      await fetch(`${API_BASE}/api/rooms/${room.room_id}/stop`, { method: 'POST' });
      await loadRooms();
    },
    [loadRooms]
  );

  return (
    <main className="manager-shell">
      <header className="manager-top">
        <div className="brand">
          <span className="brand-mark">AI</span>
          <div>
            <h1>AI 斗地主房间管理</h1>
            <p>创建房间、审批真人玩家、启动本地实时直播局</p>
          </div>
        </div>
        <a className="text-link" href="/?auto=1&players=douzero,douzero,douzero">
          快速观战
        </a>
      </header>

      <section className="manager-grid">
        <section className="room-create-panel">
          <div className="panel-head">
            <div>
              <h2>创建房间</h2>
              <p>空位会生成加入链接，管理员批准后成为 human 玩家</p>
            </div>
          </div>
          <label className="form-row">
            <span>房间名</span>
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <div className="seat-form-grid detailed">
            {players.map((player, index) => (
              <section key={index} className="seat-config">
                <div className="seat-config-head">
                  <strong>P{index}</strong>
                  <select
                    value={player.kind}
                    onChange={(event) => {
                      const next = [...players];
                      next[index] = normalizePlayerKind(player, event.target.value as RoomPlayerConfig['kind']);
                      setPlayers(next);
                    }}
                  >
                    <option value="llm">LLM 玩家</option>
                    <option value="douzero">DouZero 玩家</option>
                    <option value="human">管理员真人</option>
                    <option value="empty">空位邀请</option>
                  </select>
                </div>
                <label className="form-row compact">
                  <span>名字</span>
                  <input
                    value={player.name}
                    onChange={(event) => updatePlayerField(players, setPlayers, index, 'name', event.target.value)}
                  />
                </label>
                <label className="form-row compact">
                  <span>头像 URL</span>
                  <input
                    value={player.avatar_url}
                    onChange={(event) =>
                      updatePlayerField(players, setPlayers, index, 'avatar_url', event.target.value)
                    }
                  />
                </label>
                <label className="form-row compact">
                  <span>简介</span>
                  <textarea
                    value={player.bio}
                    onChange={(event) => updatePlayerField(players, setPlayers, index, 'bio', event.target.value)}
                  />
                </label>
                {player.kind === 'llm' && (
                  <>
                    <label className="form-row compact">
                      <span>模型</span>
                      <input
                        value={player.model}
                        onChange={(event) =>
                          updatePlayerField(players, setPlayers, index, 'model', event.target.value)
                        }
                      />
                    </label>
                    <label className="form-row compact">
                      <span>Base URL</span>
                      <input
                        value={player.base_url}
                        onChange={(event) =>
                          updatePlayerField(players, setPlayers, index, 'base_url', event.target.value)
                        }
                      />
                    </label>
                    <label className="form-row compact">
                      <span>API key</span>
                      <input
                        type="password"
                        value={player.api_key}
                        onChange={(event) =>
                          updatePlayerField(players, setPlayers, index, 'api_key', event.target.value)
                        }
                      />
                    </label>
                  </>
                )}
              </section>
            ))}
          </div>
          <div className="form-inline">
            <SeatSelector mainPlayer={mainPlayer} setMainPlayer={setMainPlayer} />
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={autoRestart}
                onChange={(event) => setAutoRestart(event.target.checked)}
              />
              一局结束后自动开局
            </label>
          </div>
          <button className="primary-button" onClick={() => void createRoom()}>
            创建房间
          </button>
          {error && <div className="error-line">{error}</div>}
        </section>

        <section className="room-list-panel">
          <div className="panel-head">
            <div>
              <h2>房间列表</h2>
              <p>{rooms.length} rooms</p>
            </div>
          </div>
          <div className="room-list">
            {rooms.map((room) => (
              <article key={room.room_id} className="room-card">
                <div className="room-card-head">
                  <div>
                    <h2>{room.name}</h2>
                    <p>{room.room_id} · {room.status}</p>
                  </div>
                  <span className={`status-pill ${room.status}`}>{room.status}</span>
                </div>
                <div className="room-seat-list">
                  {room.players.map((seat) => (
                    <div key={seat.seat} className={`room-seat ${seat.status}`}>
                      <Avatar profile={profileFromSeat(seat)} />
                      <div>
                        <strong>P{seat.seat}</strong>
                        <span>
                          {seat.label}
                          {seat.kind === 'llm' && ` · ${seat.model} · ${seat.has_api_key ? 'Key 已配置' : '缺 Key'}`}
                        </span>
                        {seat.bio && <p>{seat.bio}</p>}
                      </div>
                      {seat.status === 'pending' && (
                        <button className="small-button" onClick={() => void approve(room, seat)}>
                          <Check size={15} />
                          批准
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <div className="room-links">
                  <LinkLine label="加入链接" value={room.join_url} />
                  <LinkLine label="直播地址" value={room.stream_url} />
                </div>
                <div className="room-actions">
                  <button
                    className="icon-button"
                    onClick={() => void startRoom(room)}
                    disabled={room.players.some((seat) => seat.status !== 'ready')}
                  >
                    <Play size={17} />
                    开始
                  </button>
                  <button className="icon-button" onClick={() => void stopRoom(room)}>
                    <Square size={17} />
                    停止
                  </button>
                  <a className="icon-button" href={room.stream_url}>
                    <Eye size={17} />
                    直播页
                  </a>
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function JoinRoomView({ roomId }: { roomId: string }) {
  const [name, setName] = useState('Human Player');
  const [room, setRoom] = useState<RoomResponse | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const join = useCallback(async () => {
    setError('');
    const response = await fetch(`${API_BASE}/api/rooms/${roomId}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: name })
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail || `HTTP ${response.status}`);
      return;
    }
    setRoom((await response.json()) as RoomResponse);
    setMessage('已提交加入申请，等待管理员批准。');
  }, [name, roomId]);

  return (
    <main className="join-shell">
      <section className="join-panel">
        <div className="brand">
          <span className="brand-mark">AI</span>
          <div>
            <h1>加入斗地主房间</h1>
            <p>{roomId}</p>
          </div>
        </div>
        <label className="form-row">
          <span>玩家昵称</span>
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <button className="primary-button" onClick={() => void join()}>
          申请加入
        </button>
        {message && <div className="ok-line">{message}</div>}
        {error && <div className="error-line">{error}</div>}
        {room && <a className="text-link" href={room.stream_url}>打开直播页</a>}
      </section>
    </main>
  );
}

function StandaloneAutoView() {
  const params = new URLSearchParams(window.location.search);
  const players = params.get('players')?.split(',').filter(Boolean) ?? [
    'douzero',
    'douzero',
    'douzero'
  ];
  return <MatchStream players={players} autoStart mainPlayer={Number(params.get('main') ?? 0)} />;
}

function StreamView({ roomId }: { roomId: string }) {
  const [room, setRoom] = useState<RoomResponse | null>(null);
  const [error, setError] = useState('');

  const loadRoom = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/rooms/${roomId}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    setRoom((await response.json()) as RoomResponse);
  }, [roomId]);

  useEffect(() => {
    void loadRoom().catch((err) => setError(err instanceof Error ? err.message : String(err)));
    const interval = window.setInterval(
      () => void loadRoom().catch((err) => setError(err instanceof Error ? err.message : String(err))),
      2000
    );
    return () => window.clearInterval(interval);
  }, [loadRoom]);

  if (!room?.match_id) {
    return (
      <main className="app-shell">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">AI</span>
            <div>
              <h1>{room?.name ?? '直播房间'}</h1>
              <p>{error || '等待管理员开始房间'}</p>
            </div>
          </div>
          <a className="text-link" href="/">房间管理</a>
        </header>
        <section className="empty-live">房间尚未开局</section>
      </main>
    );
  }

  return (
    <MatchStream
      room={room}
      matchId={room.match_id}
      wsUrl={room.ws_url ?? undefined}
      mainPlayer={room.main_player}
    />
  );
}

function MatchStream({
  room,
  matchId,
  wsUrl,
  players,
  autoStart = false,
  mainPlayer = 0
}: {
  room?: RoomResponse;
  matchId?: string;
  wsUrl?: string;
  players?: string[];
  autoStart?: boolean;
  mainPlayer?: number;
}) {
  const [activeMatchId, setActiveMatchId] = useState(matchId ?? '');
  const [activeWsUrl, setActiveWsUrl] = useState(wsUrl ?? '');
  const [state, setState] = useState<GameState | null>(null);
  const [events, setEvents] = useState<MatchEvent[]>([]);
  const [profiles, setProfiles] = useState<Record<string, PlayerProfile>>({});
  const [showCounter, setShowCounter] = useState(true);
  const [showHistory, setShowHistory] = useState(true);
  const [legalActions, setLegalActions] = useState<Action[]>([]);
  const [actionError, setActionError] = useState('');
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  const [now, setNow] = useState(Date.now());
  const stateRef = useRef<GameState | null>(null);
  const eventsRef = useRef<MatchEvent[]>([]);

  const recentActions = useMemo(
    () => events.filter(isVisiblePlayEvent).slice(-18).reverse(),
    [events]
  );
  const lastPlaysByPlayer = useMemo(() => getLastPlaysByPlayer(events), [events]);
  const knownCards = useMemo(() => buildKnownCards(state), [state]);
  const timer = useMemo(() => buildTimer(events, state, now), [events, state, now]);
  const humanMainTurn =
    Boolean(activeMatchId) &&
    profiles[String(mainPlayer)]?.kind === 'human' &&
    state?.phase === 'playing' &&
    state.current_player === mainPlayer;

  const startLocalMatch = useCallback(async () => {
    const requestedPlayers = players ?? ['llm:local-llm', 'douzero', 'llm:local-private'];
    setEvents([]);
    setError('');
    const response = await fetch(`${API_BASE}/api/matches/local`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        players: requestedPlayers,
        main_player: mainPlayer,
        delay_seconds: 0.8,
        min_ai_turn_seconds: 5
      })
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const body = (await response.json()) as LocalMatchResponse;
    setActiveMatchId(body.match_id);
    setState(body.state);
    setProfiles(body.player_profiles ?? {});
    setActiveWsUrl(resolveWsUrl(body.ws_url));
  }, [mainPlayer, players]);

  useEffect(() => {
    if (matchId) {
      setActiveMatchId(matchId);
    }
    if (wsUrl) {
      setActiveWsUrl(resolveWsUrl(wsUrl));
    }
  }, [matchId, wsUrl]);

  useEffect(() => {
    if (autoStart && !window.__aiplaygame_auto_started) {
      window.__aiplaygame_auto_started = true;
      void startLocalMatch().catch((err) => setError(err instanceof Error ? err.message : String(err)));
    }
  }, [autoStart, startLocalMatch]);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    eventsRef.current = events;
    const latestProfiles = [...events]
      .reverse()
      .find((event) => event.meta?.player_profiles)?.meta.player_profiles;
    if (latestProfiles && typeof latestProfiles === 'object') {
      setProfiles(latestProfiles as Record<string, PlayerProfile>);
    }
  }, [events]);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    window.render_game_to_text = () => {
      const current = stateRef.current;
      return JSON.stringify({
        coordinate_system:
          'rectangular table with outer player info, middle hand layer, inner played-card layer, global info in right rail',
        room_id: room?.room_id ?? null,
        match_id: current?.match_id ?? (activeMatchId || null),
        phase: current?.phase ?? 'idle',
        current_player: current?.current_player ?? null,
        landlord: current?.landlord ?? null,
        winner: current?.winner ?? null,
        hand_counts: current?.hand_counts ?? {},
        latest_traces: getLatestTraces(eventsRef.current),
        recent_actions: eventsRef.current
          .filter(isVisiblePlayEvent)
          .slice(-8)
          .map((event) => ({
            seq: event.seq,
            type: event.type,
            player: event.player,
            action: event.action
          }))
      });
    };
    window.advanceTime = () => undefined;
    return () => {
      delete window.render_game_to_text;
      delete window.advanceTime;
    };
  }, [activeMatchId, room?.room_id]);

  useEffect(() => {
    if (!activeMatchId) {
      return;
    }
    void fetch(`${API_BASE}/api/matches/${activeMatchId}`)
      .then((response) => response.json())
      .then((body) => {
        if (body.state) {
          setState(body.state as GameState);
        }
        if (Array.isArray(body.events)) {
          setEvents(mergeEvents([], body.events as MatchEvent[]));
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [activeMatchId]);

  useEffect(() => {
    if (!activeWsUrl) {
      return;
    }
    const socket = new WebSocket(activeWsUrl);
    setConnected(false);
    socket.onopen = () => {
      setConnected(true);
      setError('');
    };
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setError('WebSocket connection failed');
    socket.onmessage = (message) => {
      setError('');
      const event = JSON.parse(message.data) as MatchEvent;
      setEvents((previous) => mergeEvents(previous, [event]).slice(-320));
      if (event.state && event.type !== 'decision') {
        setState(event.state);
      }
    };
    return () => socket.close();
  }, [activeWsUrl]);

  useEffect(() => {
    if (!humanMainTurn) {
      setLegalActions([]);
      setActionError('');
      return;
    }
    let cancelled = false;
    const loadLegalActions = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/matches/${activeMatchId}/legal-actions/${mainPlayer}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const body = (await response.json()) as { actions: Action[] };
        if (!cancelled) {
          setLegalActions(body.actions);
        }
      } catch (err) {
        if (!cancelled) {
          setActionError(err instanceof Error ? err.message : String(err));
        }
      }
    };
    void loadLegalActions();
    const interval = window.setInterval(() => void loadLegalActions(), 1500);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [activeMatchId, humanMainTurn, mainPlayer, events.length]);

  const submitHumanAction = useCallback(
    async (action: Action) => {
      if (!activeMatchId) {
        return;
      }
      setActionError('');
      const response = await fetch(`${API_BASE}/api/matches/${activeMatchId}/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          player: mainPlayer,
          kind: action.kind,
          cards: action.cards
        })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        setActionError(body.detail || `HTTP ${response.status}`);
        return;
      }
      setLegalActions([]);
    },
    [activeMatchId, mainPlayer]
  );

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">AI</span>
          <div>
            <h1>{room?.name ?? '斗地主直播台'}</h1>
            <p>{activeMatchId ? activeMatchId.slice(0, 12) : 'DouZero / LLM / Human Arena'}</p>
          </div>
        </div>
        <div className="toolbar">
          <span className={`status ${connected ? 'online' : ''}`}>
            {connected ? <Wifi size={18} /> : <WifiOff size={18} />}
            {connected ? '实时' : '离线'}
          </span>
          <button className="icon-button" onClick={() => setShowHistory((value) => !value)}>
            {showHistory ? <Eye size={17} /> : <EyeOff size={17} />}
            出牌记录
          </button>
          <button className="icon-button" onClick={() => setShowCounter((value) => !value)}>
            {showCounter ? <Eye size={17} /> : <EyeOff size={17} />}
            记牌器
          </button>
          {!room && (
            <button className="icon-button" onClick={() => void startLocalMatch()}>
              {activeMatchId ? <RotateCcw size={18} /> : <Play size={18} />}
              {activeMatchId ? '重开' : '开局'}
            </button>
          )}
          <button className="icon-button" onClick={toggleFullscreen}>
            <Maximize2 size={18} />
            全屏
          </button>
        </div>
      </header>

      {error && <div className="error-line">{error}</div>}

      <section className="live-layout">
        <section className="table-column">
          <section className="oval-table">
            <div className="bottom-card-zone">
              <span>底牌</span>
              <CardRow
                cards={state?.bottom_cards ?? []}
                faces={state?.card_faces?.bottom_cards ?? []}
              />
            </div>
            {[0, 1, 2].map((seat) => (
              <TablePlayerInfo
                key={seat}
                player={seat}
                state={state}
                profile={profiles[String(seat)] ?? roomSeatProfile(room?.players[seat])}
              />
            ))}
            {[0, 1, 2].map((seat) => (
              <TableHandLayer
                key={seat}
                player={seat}
                mainPlayer={mainPlayer}
                state={state}
                faces={state?.card_faces?.hands?.[String(seat)] ?? []}
                timer={timer}
              />
            ))}
            {[0, 1, 2].map((seat) => (
              <TablePlayedLayer
                key={seat}
                player={seat}
                play={state?.phase === 'playing' && state.current_player === seat
                  ? null
                  : lastPlaysByPlayer[seat] ?? null}
                active={state?.current_player === seat && state.phase !== 'finished'}
              />
            ))}
            {state?.phase === 'finished' && <WinnerOverlay state={state} />}
          </section>
          <HumanActionDock
            active={humanMainTurn}
            actions={legalActions}
            error={actionError}
            onSubmit={submitHumanAction}
          />
        </section>

        <aside className="global-rail">
          {showCounter && <MemoryPanel knownCards={knownCards} />}
          {showHistory && <HistoryPanel events={recentActions} />}
        </aside>
      </section>
    </main>
  );
}

function SeatSelector({
  mainPlayer,
  setMainPlayer
}: {
  mainPlayer: number;
  setMainPlayer: (seat: number) => void;
}) {
  return (
    <div className="segmented">
      {[0, 1, 2].map((seat) => (
        <button
          key={seat}
          className={seat === mainPlayer ? 'selected' : ''}
          onClick={() => setMainPlayer(seat)}
        >
          P{seat}
        </button>
      ))}
    </div>
  );
}

function normalizePlayerKind(
  player: RoomPlayerConfig,
  kind: RoomPlayerConfig['kind']
): RoomPlayerConfig {
  const base = { ...player, kind };
  if (kind === 'llm') {
    return {
      ...base,
      name: player.name || 'LLM 玩家',
      bio: player.bio || '大模型直接根据牌局状态选择出牌。',
      model: player.model || 'gpt-4o-mini',
      base_url: player.base_url || 'https://api.openai.com'
    };
  }
  if (kind === 'douzero') {
    return {
      ...base,
      name: player.name || 'DouZero 玩家',
      bio: player.bio || '强化学习策略玩家。',
      model: '',
      api_key: '',
      base_url: ''
    };
  }
  if (kind === 'human') {
    return {
      ...base,
      name: player.name || '管理员真人',
      bio: player.bio || '真人玩家手动控制。',
      model: '',
      api_key: '',
      base_url: ''
    };
  }
  return {
    ...base,
    name: player.name || '真人空位',
    bio: player.bio || '等待玩家通过邀请链接加入。',
    model: '',
    api_key: '',
    base_url: ''
  };
}

function updatePlayerField<K extends keyof RoomPlayerConfig>(
  players: RoomPlayerConfig[],
  setPlayers: (players: RoomPlayerConfig[]) => void,
  index: number,
  key: K,
  value: RoomPlayerConfig[K]
) {
  const next = [...players];
  next[index] = { ...next[index], [key]: value };
  setPlayers(next);
}

function LinkLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="link-line">
      <span>{label}</span>
      <a href={value}>{value}</a>
      <button className="copy-button" onClick={() => void navigator.clipboard?.writeText(value)}>
        <Copy size={14} />
      </button>
    </div>
  );
}

function TablePlayerInfo({
  player,
  state,
  profile
}: {
  player: number;
  state: GameState | null;
  profile: PlayerProfile | undefined;
}) {
  const active = state?.current_player === player && state.phase !== 'finished';
  const kindLabel = profile?.kind === 'human' ? '真人' : profile?.kind === 'llm' ? 'AI' : 'AI';
  return (
    <div className={`table-player-info seat-${player} ${active ? 'active' : ''}`}>
      <div className="badge-title">
        <Avatar profile={profile} />
        <div>
          <strong>{profile?.name || profile?.label || `P${player}`}</strong>
          <span>P{player}</span>
        </div>
        {state?.landlord === player && (
          <span className="landlord-icon" title="地主">
            <Crown size={16} />
          </span>
        )}
      </div>
      <p>{profile?.bio || profile?.kind || ''}</p>
      <div className="player-tags">
        <span>{kindLabel}</span>
      </div>
    </div>
  );
}

function TableHandLayer({
  player,
  mainPlayer,
  state,
  faces,
  timer
}: {
  player: number;
  mainPlayer: number;
  state: GameState | null;
  faces: CardFace[];
  timer: { player: number | null; remaining: number };
}) {
  const count = state?.hand_counts[String(player)] ?? 0;
  const cards = state?.hands[String(player)] ?? [];
  const active = timer.player === player && state?.phase === 'playing';
  const side = player === 1 || player === 2;
  return (
    <div className={`table-hand-layer seat-${player} ${player === mainPlayer ? 'main-view' : ''} ${active ? 'active' : ''}`}>
      {active && (
        <TurnClock
          remaining={timer.remaining}
        />
      )}
      <span className="hand-count-badge">{count}张</span>
      {player === mainPlayer ? (
        <CardRow cards={cards} faces={faces} main side={side} />
      ) : (
        <HiddenHand count={count} side={side} />
      )}
    </div>
  );
}

function TablePlayedLayer({
  player,
  play,
  active
}: {
  player: number;
  play: PlayedDisplay | null;
  active: boolean;
}) {
  const action = play?.action ?? null;
  return (
    <div className={`table-played-layer seat-${player} ${active ? 'active' : ''}`}>
      <span>P{player}</span>
      {action?.kind === 'play' ? (
        <CardRow cards={action.cards} faces={play?.faces ?? []} dense />
      ) : active && !action ? (
        <em className="active-play-placeholder">出牌中</em>
      ) : (
        <MiniAction action={action} />
      )}
    </div>
  );
}

function TurnClock({ remaining }: { remaining: number }) {
  return (
    <div className="turn-clock">
      <AlarmClock size={18} />
      <strong>{remaining}s</strong>
    </div>
  );
}

function WinnerOverlay({ state }: { state: GameState }) {
  return (
    <div className="winner-overlay">
      <strong>P{state.winner} 获胜</strong>
      <span>{state.landlord_team_won ? '地主胜' : '农民胜'}</span>
    </div>
  );
}

function HumanActionDock({
  active,
  actions,
  error,
  onSubmit
}: {
  active: boolean;
  actions: Action[];
  error: string;
  onSubmit: (action: Action) => void;
}) {
  return (
    <section className={`human-dock ${active ? 'active' : ''}`}>
      <div>
        <strong>真人操作</strong>
        <span>{active ? '选择合法动作' : '非真人主视角或未轮到操作'}</span>
      </div>
      {error && <em>{error}</em>}
      <div className="human-action-list">
        {actions.slice(0, 22).map((action, index) => (
          <button key={`${index}-${formatAction(action)}`} onClick={() => onSubmit(action)}>
            {formatAction(action)}
          </button>
        ))}
      </div>
    </section>
  );
}

function Avatar({ profile }: { profile: PlayerProfile | undefined }) {
  const kind = profile?.kind ?? 'empty';
  const Icon = kind === 'llm' ? BrainCircuit : kind === 'human' ? UserRound : Bot;
  return (
    <div className={`avatar avatar-${kind}`}>
      {profile?.avatar_url ? <img src={profile.avatar_url} alt="" /> : <Icon size={21} />}
    </div>
  );
}

function MiniAction({ action }: { action: Action | null }) {
  return (
    <div className="mini-action">
      {action?.kind === 'play' ? action.cards.join(' ') : action?.kind === 'pass' ? 'PASS' : '等待'}
    </div>
  );
}

function HistoryPanel({ events }: { events: MatchEvent[] }) {
  return (
    <section className="global-panel">
      <div className="panel-head">
        <div>
          <h2>出牌记录</h2>
          <p>{events.length} actions</p>
        </div>
      </div>
      <div className="history-list">
        {events.map((event) => (
          <div key={event.seq} className="history-item">
            <span>#{event.seq}</span>
            <strong>P{event.player}</strong>
            <em>{formatAction(event.action)}</em>
          </div>
        ))}
      </div>
    </section>
  );
}

function MemoryPanel({ knownCards }: { knownCards: Record<string, number> }) {
  return (
    <section className="global-panel">
      <div className="panel-head">
        <div>
          <h2>记牌器</h2>
          <p>剩余牌数</p>
        </div>
      </div>
      <div className="memory-grid">
        {RANKS.map((rank) => (
          <span key={rank} className="memory-chip">
            {rank}
            <b>{knownCards[rank] ?? 0}</b>
          </span>
        ))}
      </div>
    </section>
  );
}

function HiddenHand({ count, side }: { count: number; side: boolean }) {
  return (
    <div className={`hidden-card-stack ${side ? 'side-hand' : ''}`}>
      {Array.from({ length: Math.min(count, 20) }).map((_, index) => (
        <span key={index} className="card card-back" aria-hidden="true">
          <CardBackSvg />
        </span>
      ))}
    </div>
  );
}

function PlayingCard({
  card,
  face
}: {
  card: string;
  face: CardFace | null;
}) {
  const spec = getCardSvgSpec(card, face);
  return (
    <span className="card" data-card-id={spec.id}>
      <CardFaceSvg spec={spec} />
    </span>
  );
}

function CardFaceSvg({ spec }: { spec: CardSvgSpec }) {
  const joker = spec.rank === 'BJ' || spec.rank === 'RJ';
  const red = spec.suit === 'H' || spec.suit === 'D' || spec.rank === 'RJ';
  const ink = red ? '#d82835' : '#17120d';
  const accent = spec.rank === 'RJ' ? '#d82835' : spec.rank === 'BJ' ? '#1b1b1b' : ink;
  return (
    <svg className="card-svg" viewBox="0 0 64 92" role="img" aria-label={cardLabel(spec)}>
      <rect x="1.5" y="1.5" width="61" height="89" rx="7" fill="#fffaf0" stroke="#c8b58a" strokeWidth="3" />
      <path d="M5 8c7-4 17-6 30-5H10c-4 0-6 2-5 5Z" fill="rgba(255,255,255,0.86)" />
      <rect x="5" y="5" width="54" height="82" rx="5" fill="none" stroke="rgba(255,255,255,0.74)" strokeWidth="1.5" />
      {joker ? (
        <>
          <text x="9" y="18" fill={accent} fontSize="10" fontWeight="900" fontFamily="Arial, sans-serif">
            {spec.rank}
          </text>
          <text x="32" y="45" textAnchor="middle" fill={accent} fontSize="14" fontWeight="900" fontFamily="Arial, sans-serif">
            {spec.rank === 'RJ' ? 'RED' : 'BLACK'}
          </text>
          <text x="32" y="60" textAnchor="middle" fill={accent} fontSize="13" fontWeight="900" fontFamily="Arial, sans-serif">
            JOKER
          </text>
          <text x="55" y="74" fill={accent} fontSize="10" fontWeight="900" fontFamily="Arial, sans-serif" transform="rotate(180 55 74)">
            {spec.rank}
          </text>
        </>
      ) : (
        <>
          <text x="9" y="18" fill={ink} fontSize={displayRank(spec.rank).length > 1 ? '12' : '14'} fontWeight="900" fontFamily="Arial, sans-serif">
            {displayRank(spec.rank)}
          </text>
          <text x="10" y="31" fill={ink} fontSize="14" fontWeight="900" fontFamily="Arial, sans-serif">
            {displaySuit(spec.suit)}
          </text>
          <text x="32" y="58" textAnchor="middle" fill={ink} fontSize="34" fontWeight="900" fontFamily="Arial, sans-serif">
            {displaySuit(spec.suit)}
          </text>
          <g transform="rotate(180 52 74)">
            <text x="52" y="74" textAnchor="middle" fill={ink} fontSize={displayRank(spec.rank).length > 1 ? '12' : '14'} fontWeight="900" fontFamily="Arial, sans-serif">
              {displayRank(spec.rank)}
            </text>
            <text x="52" y="87" textAnchor="middle" fill={ink} fontSize="14" fontWeight="900" fontFamily="Arial, sans-serif">
              {displaySuit(spec.suit)}
            </text>
          </g>
        </>
      )}
    </svg>
  );
}

function CardBackSvg() {
  return (
    <svg className="card-svg" viewBox="0 0 64 92" role="img" aria-label="牌背">
      <rect x="1.5" y="1.5" width="61" height="89" rx="7" fill="#163f85" stroke="#c8b58a" strokeWidth="3" />
      <path d="M6 7h51v78H6z" fill="#1b5fb8" opacity="0.5" />
      <path d="M13 13h38v66H13zM7 24h50M7 36h50M7 48h50M7 60h50M7 72h50M20 7v78M32 7v78M44 7v78" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
      <rect x="7" y="7" width="50" height="78" rx="5" fill="none" stroke="rgba(255,255,255,0.54)" strokeWidth="2" />
      <path d="M20 46c8-13 16-13 24 0-8 13-16 13-24 0Z" fill="rgba(255,244,194,0.86)" />
      <circle cx="32" cy="46" r="5" fill="#12305f" />
    </svg>
  );
}

function buildCardSvgDeck(): Record<string, CardSvgSpec> {
  const entries: [string, CardSvgSpec][] = RANKS.slice(0, 13).flatMap((rank) =>
    CARD_SUITS.map((suit): [string, CardSvgSpec] => [`${rank}${suit}`, { id: `${rank}${suit}`, rank, suit }])
  );
  entries.push(['BJ', { id: 'BJ', rank: 'BJ', suit: 'BJ' }]);
  entries.push(['RJ', { id: 'RJ', rank: 'RJ', suit: 'RJ' }]);
  return Object.fromEntries(entries);
}

function getCardSvgSpec(card: string, face: CardFace | null): CardSvgSpec {
  if (face?.id && CARD_SVG_DECK[face.id]) {
    return CARD_SVG_DECK[face.id];
  }
  if (CARD_SVG_DECK[card]) {
    return CARD_SVG_DECK[card];
  }
  if (face) {
    return { id: face.id, rank: face.rank, suit: face.suit };
  }
  const fallback = RANKS.includes(card) ? `${card}S` : card;
  return CARD_SVG_DECK[fallback] ?? { id: card, rank: card, suit: 'S' };
}

function cardLabel(spec: CardSvgSpec) {
  if (spec.rank === 'BJ') {
    return '小王';
  }
  if (spec.rank === 'RJ') {
    return '大王';
  }
  return `${displaySuit(spec.suit)}${displayRank(spec.rank)}`;
}

function displayRank(rank: string) {
  return rank === 'T' ? '10' : rank;
}

function displaySuit(suit: string) {
  return {
    S: '♠',
    H: '♥',
    C: '♣',
    D: '♦'
  }[suit] ?? suit;
}

function CardRow({
  cards,
  faces = [],
  dense = false,
  main = false,
  side = false
}: {
  cards: string[];
  faces?: CardFace[];
  dense?: boolean;
  main?: boolean;
  side?: boolean;
}) {
  const seenRanks = new Map<string, number>();
  return (
    <div className={`card-row ${dense ? 'dense' : ''} ${main ? 'main-hand' : ''} ${side ? 'side-hand' : ''}`}>
      {cards.map((card, index) => {
        const occurrence = seenRanks.get(card) ?? 0;
        seenRanks.set(card, occurrence + 1);
        return (
          <PlayingCard
            key={`${card}-${index}`}
            card={card}
            face={faces[index] ?? fallbackFaceForCard(card, occurrence)}
          />
        );
      })}
    </div>
  );
}

function fallbackFaceForCard(card: string, occurrence: number): CardFace | null {
  if (card === 'BJ' || card === 'RJ') {
    return { id: card, rank: card, suit: card };
  }
  if (!RANKS.includes(card)) {
    return null;
  }
  const suit = CARD_SUITS[occurrence % CARD_SUITS.length];
  return { id: `${card}${suit}`, rank: card, suit };
}

function getLastPlaysByPlayer(events: MatchEvent[]) {
  const result: Record<number, PlayedDisplay | null> = { 0: null, 1: null, 2: null };
  for (const event of events) {
    if (isVisiblePlayEvent(event) && event.player !== null && event.action) {
      result[event.player] = {
        action: event.action,
        faces: event.action.kind === 'play' ? actionFaces(event) : []
      };
    }
  }
  return result;
}

function actionFaces(event: MatchEvent): CardFace[] {
  const raw = event.meta.action_faces;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter(isCardFace);
}

function isCardFace(value: unknown): value is CardFace {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === 'string' &&
    typeof candidate.rank === 'string' &&
    typeof candidate.suit === 'string'
  );
}

function mergeEvents(previous: MatchEvent[], incoming: MatchEvent[]) {
  const byKey = new Map<string, MatchEvent>();
  for (const event of [...previous, ...incoming]) {
    byKey.set(`${event.match_id}:${event.seq}`, event);
  }
  return [...byKey.values()].sort((left, right) => left.seq - right.seq);
}

function isVisiblePlayEvent(event: MatchEvent) {
  return event.action !== null && (event.type === 'play' || event.type === 'pass');
}

function getLatestTraces(events: MatchEvent[]) {
  const result: Record<number, DecisionTrace | null> = { 0: null, 1: null, 2: null };
  for (const event of events) {
    if (event.trace) {
      result[event.trace.player] = event.trace;
    }
  }
  return result;
}

function buildKnownCards(state: GameState | null): Record<string, number> {
  if (!state) {
    return Object.fromEntries(RANKS.map((rank) => [rank, rank.includes('J') ? 1 : 4]));
  }
  return state.remaining_deck_counts;
}

function buildTimer(events: MatchEvent[], state: GameState | null, now: number) {
  if (!state || state.phase === 'finished') {
    return { player: null, remaining: TURN_SECONDS };
  }
  const lastStateEvent = [...events]
    .reverse()
    .find(
      (event) =>
        event.type !== 'decision' &&
        event.state?.current_player === state.current_player
    );
  const elapsed = lastStateEvent ? Math.floor(now / 1000 - lastStateEvent.ts) : 0;
  return {
    player: state.current_player,
    remaining: Math.max(0, Math.min(TURN_SECONDS, TURN_SECONDS - elapsed))
  };
}

function formatAction(action: Action | null) {
  if (!action) {
    return '-';
  }
  if (action.kind === 'pass') {
    return 'PASS';
  }
  if (action.kind === 'bid') {
    return `叫分 ${action.bid}`;
  }
  return action.cards.join(' ');
}

function resolveWsUrl(raw: string) {
  if (raw.startsWith('ws://') || raw.startsWith('wss://')) {
    return raw;
  }
  const base = new URL(API_BASE);
  base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
  base.pathname = raw;
  return base.toString();
}

function profileFromSeat(seat: RoomSeat): PlayerProfile {
  return {
    kind: seat.kind,
    label: seat.label,
    name: seat.name,
    avatar_url: seat.avatar_url,
    bio: seat.bio,
    model: seat.model,
    endpoint: seat.base_url
  };
}

function roomSeatProfile(seat: RoomSeat | undefined): PlayerProfile | undefined {
  return seat ? profileFromSeat(seat) : undefined;
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    void document.documentElement.requestFullscreen();
  } else {
    void document.exitFullscreen();
  }
}
