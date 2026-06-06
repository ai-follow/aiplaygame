from aiplaygame.core.models import Action
from aiplaygame.core.rules import can_beat, classify_cards, legal_actions


def pattern(cards):
    result = classify_cards(cards)
    assert result is not None
    return result.type


def test_classifies_core_patterns():
    assert pattern(["3"]) == "single"
    assert pattern(["3", "3"]) == "pair"
    assert pattern(["3", "3", "3"]) == "triple"
    assert pattern(["3", "3", "3", "4"]) == "triple_single"
    assert pattern(["3", "3", "3", "4", "4"]) == "triple_pair"
    assert pattern(["3", "4", "5", "6", "7"]) == "straight"
    assert pattern(["3", "3", "4", "4", "5", "5"]) == "pair_straight"
    assert pattern(["3", "3", "3", "4", "4", "4"]) == "airplane"
    assert pattern(["3", "3", "3", "4", "4", "4", "5", "6"]) == "airplane_single"
    assert pattern(["3", "3", "3", "4", "4", "4", "5", "5", "6", "6"]) == "airplane_pair"
    assert pattern(["9", "9", "9", "9"]) == "bomb"
    assert pattern(["BJ", "RJ"]) == "rocket"


def test_rejects_invalid_chains():
    assert classify_cards(["T", "J", "Q", "K", "A", "2"]) is None
    assert classify_cards(["3", "3", "4", "5", "6"]) is None
    assert classify_cards(["BJ", "RJ", "3"]) is None


def test_beating_rules():
    assert can_beat(["4"], ["3"])
    assert not can_beat(["3"], ["4"])
    assert can_beat(["4", "4"], ["3", "3"])
    assert can_beat(["9", "9", "9", "9"], ["A", "A", "A"])
    assert can_beat(["BJ", "RJ"], ["9", "9", "9", "9"])
    assert not can_beat(["3", "4", "5", "6", "7"], ["4", "5", "6", "7", "8"])


def test_legal_actions_include_pass_and_beating_play():
    hand = ["3", "4", "4", "5", "6", "7", "8", "9", "T"]
    actions = legal_actions(hand, Action.play(1, ["3"]), player=0)
    assert Action.pass_turn(0) in actions
    assert Action.play(0, ["4"]) in actions
    assert Action.play(0, ["3"]) not in actions


def test_pass_not_available_when_leading():
    hand = ["3", "4", "5", "6", "7"]
    actions = legal_actions(hand, None, player=0)
    assert Action.pass_turn(0) not in actions
    assert Action.play(0, ["3", "4", "5", "6", "7"]) in actions
