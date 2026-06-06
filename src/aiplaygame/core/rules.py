from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Literal

from aiplaygame.core.cards import CHAIN_RANKS, JOKERS, RANK_VALUE, RANKS, Rank, sort_cards
from aiplaygame.core.models import Action

PatternType = Literal[
    "single",
    "pair",
    "triple",
    "triple_single",
    "triple_pair",
    "straight",
    "pair_straight",
    "airplane",
    "airplane_single",
    "airplane_pair",
    "bomb",
    "rocket",
]


@dataclass(frozen=True)
class HandPattern:
    type: PatternType
    main_rank: Rank
    length: int
    sequence_length: int = 1

    @property
    def strength(self) -> tuple[int, int, int]:
        type_order = {
            "single": 1,
            "pair": 2,
            "triple": 3,
            "triple_single": 4,
            "triple_pair": 5,
            "straight": 6,
            "pair_straight": 7,
            "airplane": 8,
            "airplane_single": 9,
            "airplane_pair": 10,
            "bomb": 11,
            "rocket": 12,
        }
        return (type_order[self.type], self.sequence_length, RANK_VALUE[self.main_rank])


class InvalidPlay(ValueError):
    pass


def classify_cards(cards: list[Rank]) -> HandPattern | None:
    cards = sort_cards(cards)
    total = len(cards)
    if total == 0:
        return None

    counts = Counter(cards)
    unique = list(counts)
    count_values = sorted(counts.values(), reverse=True)

    if total == 2 and set(cards) == set(JOKERS):
        return HandPattern("rocket", "RJ", total)

    if len(unique) == 1:
        rank = unique[0]
        if total == 1:
            return HandPattern("single", rank, total)
        if total == 2 and rank not in JOKERS:
            return HandPattern("pair", rank, total)
        if total == 3 and rank not in JOKERS:
            return HandPattern("triple", rank, total)
        if total == 4 and rank not in JOKERS:
            return HandPattern("bomb", rank, total)

    if total == 4 and count_values == [3, 1]:
        triple_rank = _rank_with_count(counts, 3)
        return HandPattern("triple_single", triple_rank, total)

    if total == 5 and count_values == [3, 2]:
        triple_rank = _rank_with_count(counts, 3)
        return HandPattern("triple_pair", triple_rank, total)

    if _is_chain(unique, min_len=5) and all(count == 1 for count in counts.values()):
        return HandPattern("straight", unique[-1], total, len(unique))

    if (
        total >= 6
        and total % 2 == 0
        and all(count == 2 for count in counts.values())
        and _is_chain(unique, min_len=3)
    ):
        return HandPattern("pair_straight", unique[-1], total, len(unique))

    airplane = _classify_airplane(counts, total)
    if airplane is not None:
        return airplane

    return None


def assert_valid_play(cards: list[Rank]) -> HandPattern:
    pattern = classify_cards(cards)
    if pattern is None:
        raise InvalidPlay(f"Invalid 斗地主 play: {cards!r}")
    return pattern


def can_beat(candidate: list[Rank], previous: list[Rank] | None) -> bool:
    candidate_pattern = classify_cards(candidate)
    if candidate_pattern is None:
        return False
    if not previous:
        return True

    previous_pattern = classify_cards(previous)
    if previous_pattern is None:
        raise InvalidPlay(f"Previous action is invalid: {previous!r}")

    if candidate_pattern.type == "rocket":
        return previous_pattern.type != "rocket"
    if previous_pattern.type == "rocket":
        return False
    if candidate_pattern.type == "bomb" and previous_pattern.type != "bomb":
        return True
    if candidate_pattern.type != previous_pattern.type:
        return False
    if candidate_pattern.length != previous_pattern.length:
        return False
    if candidate_pattern.sequence_length != previous_pattern.sequence_length:
        return False
    return RANK_VALUE[candidate_pattern.main_rank] > RANK_VALUE[previous_pattern.main_rank]


def legal_actions(hand: list[Rank], last_action: Action | None, player: int) -> list[Action]:
    previous_cards = _active_previous_cards(last_action, player)
    plays = generate_plays(hand)
    if previous_cards is None:
        return [Action.play(player, cards) for cards in plays]

    beating = [Action.play(player, cards) for cards in plays if can_beat(cards, previous_cards)]
    return [Action.pass_turn(player), *beating]


def generate_plays(hand: list[Rank]) -> list[list[Rank]]:
    counts = Counter(hand)
    plays: set[tuple[Rank, ...]] = set()

    def add(cards: list[Rank]) -> None:
        if classify_cards(cards) is not None:
            plays.add(tuple(sort_cards(cards)))

    for rank in RANKS:
        if counts[rank] >= 1:
            add([rank])
        if counts[rank] >= 2 and rank not in JOKERS:
            add([rank, rank])
        if counts[rank] >= 3 and rank not in JOKERS:
            add([rank, rank, rank])
        if counts[rank] == 4 and rank not in JOKERS:
            add([rank] * 4)

    if counts["BJ"] and counts["RJ"]:
        add(["BJ", "RJ"])

    for sequence in _available_sequences(counts, min_len=5, per_rank=1):
        add(sequence)

    for sequence in _available_sequences(counts, min_len=3, per_rank=2):
        add([rank for rank in sequence for _ in range(2)])

    triple_ranks = [rank for rank in RANKS[:13] if counts[rank] >= 3]
    single_ranks = [rank for rank in RANKS if counts[rank] >= 1]
    pair_ranks = [rank for rank in RANKS[:13] if counts[rank] >= 2]
    for triple_rank in triple_ranks:
        for single_rank in single_ranks:
            if single_rank != triple_rank and counts[single_rank] >= 1:
                add([triple_rank] * 3 + [single_rank])
        for pair_rank in pair_ranks:
            if pair_rank != triple_rank and counts[pair_rank] >= 2:
                add([triple_rank] * 3 + [pair_rank] * 2)

    for triple_sequence in _available_sequences(counts, min_len=2, per_rank=3):
        k = len(triple_sequence)
        triples = [rank for rank in triple_sequence for _ in range(3)]
        add(triples)

        attachment_single_ranks = [
            rank for rank in RANKS if rank not in triple_sequence and counts[rank] >= 1
        ]
        for attachments in combinations(attachment_single_ranks, k):
            add(triples + list(attachments))

        attachment_pair_ranks = [
            rank for rank in RANKS[:13] if rank not in triple_sequence and counts[rank] >= 2
        ]
        for attachments in combinations(attachment_pair_ranks, k):
            add(triples + [rank for rank in attachments for _ in range(2)])

    return sorted(
        (list(cards) for cards in plays),
        key=lambda cards: (
            len(cards),
            classify_cards(cards).strength if classify_cards(cards) else (99, 99, 99),
            [RANK_VALUE[rank] for rank in cards],
        ),
    )


def _active_previous_cards(last_action: Action | None, player: int) -> list[Rank] | None:
    if last_action is None or last_action.kind != "play":
        return None
    if last_action.player == player:
        return None
    return last_action.cards


def _rank_with_count(counts: Counter[Rank], target: int) -> Rank:
    for rank in RANKS:
        if counts[rank] == target:
            return rank
    raise InvalidPlay(f"No rank with count {target}: {counts!r}")


def _is_chain(ranks: list[Rank], min_len: int) -> bool:
    if len(ranks) < min_len:
        return False
    values = [RANK_VALUE[rank] for rank in ranks]
    if any(rank not in CHAIN_RANKS for rank in ranks):
        return False
    return values == list(range(values[0], values[0] + len(values)))


def _available_sequences(counts: Counter[Rank], min_len: int, per_rank: int) -> list[list[Rank]]:
    eligible = [rank for rank in CHAIN_RANKS if counts[rank] >= per_rank]
    sequences: list[list[Rank]] = []
    start = 0
    while start < len(eligible):
        end = start + 1
        while (
            end < len(eligible)
            and RANK_VALUE[eligible[end]] == RANK_VALUE[eligible[end - 1]] + 1
        ):
            end += 1
        run = eligible[start:end]
        for length in range(min_len, len(run) + 1):
            for offset in range(0, len(run) - length + 1):
                sequences.append(run[offset : offset + length])
        start = end
    return sequences


def _classify_airplane(counts: Counter[Rank], total: int) -> HandPattern | None:
    triple_ranks = [rank for rank in CHAIN_RANKS if counts[rank] >= 3]
    for sequence in sorted(
        _continuous_subsequences(triple_ranks, min_len=2),
        key=lambda seq: (-len(seq), RANK_VALUE[seq[-1]]),
    ):
        k = len(sequence)
        rest = counts.copy()
        for rank in sequence:
            rest[rank] -= 3
            if rest[rank] == 0:
                del rest[rank]

        if total == 3 * k and not rest:
            return HandPattern("airplane", sequence[-1], total, k)

        if (
            total == 4 * k
            and sum(rest.values()) == k
            and all(value == 1 for value in rest.values())
        ):
            return HandPattern("airplane_single", sequence[-1], total, k)

        if (
            total == 5 * k
            and sum(rest.values()) == 2 * k
            and len(rest) == k
            and all(value == 2 for value in rest.values())
            and all(rank not in JOKERS for rank in rest)
        ):
            return HandPattern("airplane_pair", sequence[-1], total, k)

    return None


def _continuous_subsequences(ranks: list[Rank], min_len: int) -> list[list[Rank]]:
    sequences: list[list[Rank]] = []
    start = 0
    while start < len(ranks):
        end = start + 1
        while end < len(ranks) and RANK_VALUE[ranks[end]] == RANK_VALUE[ranks[end - 1]] + 1:
            end += 1
        run = ranks[start:end]
        for length in range(min_len, len(run) + 1):
            for offset in range(0, len(run) - length + 1):
                sequences.append(run[offset : offset + length])
        start = end
    return sequences
