import type { RoomPlayerConfig } from './types';

export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
export const RANKS = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A', '2', 'BJ', 'RJ'];
export const CARD_SUITS = ['S', 'H', 'C', 'D'] as const;
export const TURN_SECONDS = 30;

export const DEFAULT_PLAYERS: RoomPlayerConfig[] = [
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
