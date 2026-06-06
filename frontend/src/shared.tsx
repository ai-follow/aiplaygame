import { Bot, BrainCircuit, Copy, UserRound } from 'lucide-react';

import type { PlayerProfile } from './types';

export function SeatSelector({
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

export function LinkLine({ label, value }: { label: string; value: string }) {
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

export function Avatar({ profile }: { profile: PlayerProfile | undefined }) {
  const kind = profile?.kind ?? 'empty';
  const Icon = kind === 'llm' ? BrainCircuit : kind === 'human' ? UserRound : Bot;
  return (
    <div className={`avatar avatar-${kind}`}>
      {profile?.avatar_url ? <img src={profile.avatar_url} alt="" /> : <Icon size={21} />}
    </div>
  );
}
