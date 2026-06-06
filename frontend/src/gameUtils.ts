import { API_BASE, RANKS, TURN_SECONDS } from './constants';
import type {
  Action,
  CardFace,
  DecisionTrace,
  GameState,
  MatchEvent,
  PlayerProfile,
  RoomSeat
} from './types';

export type PlayedDisplay = {
  action: Action;
  faces: CardFace[];
};

export function getLastPlaysByPlayer(events: MatchEvent[]) {
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

export function mergeEvents(previous: MatchEvent[], incoming: MatchEvent[]) {
  const byKey = new Map<string, MatchEvent>();
  for (const event of [...previous, ...incoming]) {
    byKey.set(`${event.match_id}:${event.seq}`, event);
  }
  return [...byKey.values()].sort((left, right) => left.seq - right.seq);
}

export function isVisiblePlayEvent(event: MatchEvent) {
  return event.action !== null && (event.type === 'play' || event.type === 'pass');
}

export function getLatestTraces(events: MatchEvent[]) {
  const result: Record<number, DecisionTrace | null> = { 0: null, 1: null, 2: null };
  for (const event of events) {
    if (event.trace) {
      result[event.trace.player] = event.trace;
    }
  }
  return result;
}

export function buildKnownCards(state: GameState | null): Record<string, number> {
  if (!state) {
    return Object.fromEntries(RANKS.map((rank) => [rank, rank.includes('J') ? 1 : 4]));
  }
  return state.remaining_deck_counts;
}

export function buildTimer(events: MatchEvent[], state: GameState | null, now: number) {
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

export function formatAction(action: Action | null) {
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

export function resolveWsUrl(raw: string) {
  if (raw.startsWith('ws://') || raw.startsWith('wss://')) {
    return raw;
  }
  const base = new URL(API_BASE);
  base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
  base.pathname = raw;
  return base.toString();
}

export function profileFromSeat(seat: RoomSeat): PlayerProfile {
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

export function roomSeatProfile(seat: RoomSeat | undefined): PlayerProfile | undefined {
  return seat ? profileFromSeat(seat) : undefined;
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
