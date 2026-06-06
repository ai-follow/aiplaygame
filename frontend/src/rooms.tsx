import { Check, Eye, Play, Square } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { API_BASE, DEFAULT_PLAYERS } from './constants';
import { profileFromSeat } from './gameUtils';
import { Avatar, LinkLine, SeatSelector } from './shared';
import type { PlayerProfile, RoomPlayerConfig, RoomResponse, RoomSeat } from './types';

export function RoomManager() {
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
              <SeatConfig
                key={index}
                index={index}
                player={player}
                players={players}
                setPlayers={setPlayers}
              />
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
              <RoomCard key={room.room_id} room={room} approve={approve} startRoom={startRoom} stopRoom={stopRoom} />
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

export function JoinRoomView({ roomId }: { roomId: string }) {
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

function SeatConfig({
  index,
  player,
  players,
  setPlayers
}: {
  index: number;
  player: RoomPlayerConfig;
  players: RoomPlayerConfig[];
  setPlayers: (players: RoomPlayerConfig[]) => void;
}) {
  return (
    <section className="seat-config">
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
      <PlayerTextField label="名字" value={player.name} onChange={(value) => updatePlayerField(players, setPlayers, index, 'name', value)} />
      <PlayerTextField label="头像 URL" value={player.avatar_url} onChange={(value) => updatePlayerField(players, setPlayers, index, 'avatar_url', value)} />
      <label className="form-row compact">
        <span>简介</span>
        <textarea
          value={player.bio}
          onChange={(event) => updatePlayerField(players, setPlayers, index, 'bio', event.target.value)}
        />
      </label>
      {player.kind === 'llm' && (
        <>
          <PlayerTextField label="模型" value={player.model} onChange={(value) => updatePlayerField(players, setPlayers, index, 'model', value)} />
          <PlayerTextField label="Base URL" value={player.base_url} onChange={(value) => updatePlayerField(players, setPlayers, index, 'base_url', value)} />
          <label className="form-row compact">
            <span>API key</span>
            <input
              type="password"
              value={player.api_key}
              onChange={(event) => updatePlayerField(players, setPlayers, index, 'api_key', event.target.value)}
            />
          </label>
        </>
      )}
    </section>
  );
}

function PlayerTextField({
  label,
  value,
  onChange
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="form-row compact">
      <span>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function RoomCard({
  room,
  approve,
  startRoom,
  stopRoom
}: {
  room: RoomResponse;
  approve: (room: RoomResponse, seat: RoomSeat) => Promise<void>;
  startRoom: (room: RoomResponse) => Promise<void>;
  stopRoom: (room: RoomResponse) => Promise<void>;
}) {
  return (
    <article className="room-card">
      <div className="room-card-head">
        <div>
          <h2>{room.name}</h2>
          <p>{room.room_id} · {room.status}</p>
        </div>
        <span className={`status-pill ${room.status}`}>{room.status}</span>
      </div>
      <div className="room-seat-list">
        {room.players.map((seat) => (
          <RoomSeatItem key={seat.seat} seat={seat} onApprove={() => void approve(room, seat)} />
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
  );
}

function RoomSeatItem({ seat, onApprove }: { seat: RoomSeat; onApprove: () => void }) {
  return (
    <div className={`room-seat ${seat.status}`}>
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
        <button className="small-button" onClick={onApprove}>
          <Check size={15} />
          批准
        </button>
      )}
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
