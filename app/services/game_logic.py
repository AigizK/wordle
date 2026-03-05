from __future__ import annotations

from collections import Counter

STATE_TO_CODE = {"correct": "C", "present": "P", "absent": "A"}
CODE_TO_STATE = {"C": "correct", "P": "present", "A": "absent"}


def evaluate_guess(guess: str, answer: str) -> list[str]:
    guess_arr = list(guess)
    ans_arr = list(answer)
    result = ["absent"] * len(guess_arr)

    counts = Counter(ans_arr)

    for i, char in enumerate(guess_arr):
        if char == ans_arr[i]:
            result[i] = "correct"
            counts[char] -= 1

    for i, char in enumerate(guess_arr):
        if result[i] == "correct":
            continue
        if counts[char] > 0:
            result[i] = "present"
            counts[char] -= 1

    return result


def encode_result_mask(states: list[str]) -> str:
    return "".join(STATE_TO_CODE[state] for state in states)


def decode_result_mask(mask: str) -> list[str]:
    return [CODE_TO_STATE[ch] for ch in mask]


def is_win_mask(mask: str) -> bool:
    return set(mask) == {"C"}
