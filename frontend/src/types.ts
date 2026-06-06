export type ActionKind = 'bid' | 'play' | 'pass';
export type EventType =
  | 'deal'
  | 'bid'
  | 'turn_start'
  | 'play'
  | 'pass'
  | 'decision'
  | 'game_over'
  | 'error';

export interface Action {
  kind: ActionKind;
  player: number | null;
  cards: string[];
  bid: number | null;
}

export interface CardFace {
  id: string;
  rank: string;
  suit: string;
}

export interface DecisionTrace {
  player: number;
  selected: Action;
  candidates: Action[];
  win_rate: number;
  elapsed_ms: number;
  fallback: boolean;
  reason: string;
  agent_kind: string;
  thought: string;
  public_thought: string;
}

export interface GameState {
  match_id: string;
  phase: 'dealing' | 'bidding' | 'playing' | 'finished';
  landlord: number | null;
  current_player: number;
  bottom_cards: string[];
  hands: Record<string, string[]>;
  hand_counts: Record<string, number>;
  last_action: Action | null;
  last_player: number | null;
  pass_count: number;
  history: Action[];
  played_cards: string[];
  card_faces: {
    hands?: Record<string, CardFace[]>;
    bottom_cards?: CardFace[];
    played_cards?: CardFace[];
  };
  remaining_deck_counts: Record<string, number>;
  winner: number | null;
  landlord_team_won: boolean | null;
}

export interface MatchEvent {
  type: EventType;
  match_id: string;
  seq: number;
  ts: number;
  player: number | null;
  action: Action | null;
  state: GameState | null;
  trace: DecisionTrace | null;
  message: string;
  meta: Record<string, unknown>;
}

export interface PlayerProfile {
  kind: string;
  label: string;
  name?: string;
  avatar_url?: string;
  bio?: string;
  model: string;
  endpoint: string;
}

export interface RoomPlayerConfig {
  kind: 'llm' | 'douzero' | 'human' | 'empty';
  name: string;
  avatar_url: string;
  bio: string;
  model: string;
  api_key: string;
  base_url: string;
}

export interface LocalMatchResponse {
  match_id: string;
  ws_url: string;
  state: GameState;
  main_player: number;
  player_profiles: Record<string, PlayerProfile>;
}

export interface RoomSeat {
  seat: number;
  kind: 'llm' | 'douzero' | 'human' | 'empty';
  label: string;
  name: string;
  avatar_url: string;
  bio: string;
  model: string;
  base_url: string;
  has_api_key: boolean;
  status: 'ready' | 'open' | 'pending';
  request_id: string | null;
  display_name: string;
}

export interface RoomResponse {
  room_id: string;
  name: string;
  status: 'waiting' | 'running' | 'stopped';
  players: RoomSeat[];
  main_player: number;
  auto_restart: boolean;
  match_id: string | null;
  join_url: string;
  stream_url: string;
  ws_url: string | null;
}
