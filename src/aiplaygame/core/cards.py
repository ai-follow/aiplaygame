from __future__ import annotations

from collections import Counter
from random import Random

Rank = str

RANKS: tuple[Rank, ...] = (
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "T",
    "J",
    "Q",
    "K",
    "A",
    "2",
    "BJ",
    "RJ",
)
CHAIN_RANKS: tuple[Rank, ...] = RANKS[:12]
JOKERS: tuple[Rank, Rank] = ("BJ", "RJ")
RANK_VALUE: dict[Rank, int] = {rank: index for index, rank in enumerate(RANKS)}


def normalize_card(card: str | int) -> Rank:
    """Normalize common card encodings to the project rank string."""
    if isinstance(card, int):
        if 0 <= card < len(RANKS):
            return RANKS[card]
        raise ValueError(f"Unknown numeric card rank: {card!r}")

    token = str(card).strip().upper()
    aliases = {
        "10": "T",
        "X": "BJ",
        "BLACKJOKER": "BJ",
        "BLACK_JOKER": "BJ",
        "SMALL_JOKER": "BJ",
        "SJ": "BJ",
        "Y": "RJ",
        "REDJOKER": "RJ",
        "RED_JOKER": "RJ",
        "BIG_JOKER": "RJ",
        "BJOKER": "RJ",
    }
    token = aliases.get(token, token)
    if token not in RANK_VALUE:
        raise ValueError(f"Unknown card rank: {card!r}")
    return token


def normalize_cards(cards: list[str | int] | tuple[str | int, ...]) -> list[Rank]:
    return sort_cards([normalize_card(card) for card in cards])


def sort_cards(cards: list[Rank]) -> list[Rank]:
    return sorted(cards, key=lambda card: (RANK_VALUE[card], card))


def deck() -> list[Rank]:
    cards: list[Rank] = []
    for rank in RANKS[:13]:
        cards.extend([rank] * 4)
    cards.extend(JOKERS)
    return cards


def shuffled_deck(seed: int | None = None) -> list[Rank]:
    cards = deck()
    rng = Random(seed)
    rng.shuffle(cards)
    return cards


def card_counter(cards: list[Rank]) -> Counter[Rank]:
    return Counter(cards)


def remove_cards(hand: list[Rank], cards: list[Rank]) -> list[Rank]:
    counts = Counter(hand)
    removing = Counter(cards)
    missing = removing - counts
    if missing:
        raise ValueError(f"Cannot remove cards not in hand: {dict(missing)}")
    counts.subtract(removing)
    result: list[Rank] = []
    for rank in RANKS:
        result.extend([rank] * counts[rank])
    return result


def contains_cards(hand: list[Rank], cards: list[Rank]) -> bool:
    return not (Counter(cards) - Counter(hand))


def count_played(history: list[list[Rank]]) -> Counter[Rank]:
    counts: Counter[Rank] = Counter()
    for cards in history:
        counts.update(cards)
    return counts
