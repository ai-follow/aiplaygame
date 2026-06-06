import { AlarmClock, Crown } from 'lucide-react';

import { CardRow, HiddenHand } from './cards';
import { RANKS } from './constants';
import { formatAction, roomSeatProfile, type PlayedDisplay } from './gameUtils';
import { Avatar } from './shared';
import type { Action, CardFace, GameState, MatchEvent, PlayerProfile, RoomResponse } from './types';

export function MatchTable({
  state,
  profiles,
  room,
  mainPlayer,
  lastPlaysByPlayer,
  timer
}: {
  state: GameState | null;
  profiles: Record<string, PlayerProfile>;
  room?: RoomResponse;
  mainPlayer: number;
  lastPlaysByPlayer: Record<number, PlayedDisplay | null>;
  timer: { player: number | null; remaining: number };
}) {
  return (
    <section className="oval-table">
      <div className="bottom-card-zone">
        <span>底牌</span>
        <CardRow
          cards={state?.bottom_cards ?? []}
          faces={state?.card_faces?.bottom_cards ?? []}
        />
      </div>
      {state?.phase === 'finished' && <WinnerBanner state={state} profiles={profiles} />}
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
          remaining={timer.player === seat ? timer.remaining : null}
        />
      ))}
    </section>
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
          <strong>{playerName(player, profile)}</strong>
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
  faces
}: {
  player: number;
  mainPlayer: number;
  state: GameState | null;
  faces: CardFace[];
}) {
  const count = state?.hand_counts[String(player)] ?? 0;
  const cards = state?.hands[String(player)] ?? [];
  const side = player === 1 || player === 2;
  const showFaces = player === mainPlayer || state?.phase === 'finished';
  return (
    <div className={`table-hand-layer seat-${player} ${player === mainPlayer ? 'main-view' : ''}`}>
      <span className="hand-count-badge">{count}张</span>
      {showFaces ? (
        <CardRow cards={cards} faces={faces} main={player === mainPlayer} side={side} />
      ) : (
        <HiddenHand count={count} side={side} />
      )}
    </div>
  );
}

function TablePlayedLayer({
  player,
  play,
  active,
  remaining
}: {
  player: number;
  play: PlayedDisplay | null;
  active: boolean;
  remaining: number | null;
}) {
  const action = play?.action ?? null;
  return (
    <div className={`table-played-layer seat-${player} ${active ? 'active' : ''}`}>
      {active && remaining !== null ? (
        <TurnClock remaining={remaining} />
      ) : action?.kind === 'play' ? (
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

function WinnerBanner({ state, profiles }: { state: GameState; profiles: Record<string, PlayerProfile> }) {
  const landlord = state.landlord;
  const winnerText =
    state.landlord_team_won && landlord !== null
      ? `${playerName(landlord, profiles[String(landlord)])}（地主）获胜`
      : [0, 1, 2]
          .filter((player) => player !== landlord)
          .map((player) => playerName(player, profiles[String(player)]))
          .join('、') + '（农民）获胜';

  return <div className="winner-banner">{winnerText}</div>;
}

export function HumanActionDock({
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

export function HistoryPanel({ events }: { events: MatchEvent[] }) {
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

export function MemoryPanel({ knownCards }: { knownCards: Record<string, number> }) {
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

function MiniAction({ action }: { action: Action | null }) {
  return (
    <div className="mini-action">
      {action?.kind === 'play' ? action.cards.join(' ') : action?.kind === 'pass' ? 'PASS' : '等待'}
    </div>
  );
}

function playerName(player: number, profile: PlayerProfile | undefined) {
  return profile?.name || profile?.label || `P${player}`;
}
