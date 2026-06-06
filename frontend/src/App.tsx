import {
  Eye,
  EyeOff,
  Maximize2,
  Play,
  RotateCcw,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { API_BASE } from './constants';
import {
  buildKnownCards,
  buildTimer,
  getLastPlaysByPlayer,
  getLatestTraces,
  isVisiblePlayEvent,
  mergeEvents,
  resolveWsUrl
} from './gameUtils';
import { JoinRoomView, RoomManager } from './rooms';
import { HistoryPanel, HumanActionDock, MatchTable, MemoryPanel } from './table';
import type {
  Action,
  GameState,
  LocalMatchResponse,
  MatchEvent,
  PlayerProfile,
  RoomResponse
} from './types';

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
          <MatchTable
            state={state}
            profiles={profiles}
            room={room}
            mainPlayer={mainPlayer}
            lastPlaysByPlayer={lastPlaysByPlayer}
            timer={timer}
          />
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

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    void document.documentElement.requestFullscreen();
  } else {
    void document.exitFullscreen();
  }
}
