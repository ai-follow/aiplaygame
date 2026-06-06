import { CARD_SUITS, RANKS } from './constants';
import type { CardFace } from './types';

type CardSvgSpec = {
  id: string;
  rank: string;
  suit: string;
};

const CARD_SVG_DECK = buildCardSvgDeck();

export function HiddenHand({ count, side }: { count: number; side: boolean }) {
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

export function CardRow({
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
