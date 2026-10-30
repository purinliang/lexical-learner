# backend/tests/test_generate_cloze.py
# Test complete-word replacement, phrases, inflection and invalid answers offline.

import pytest

from lexical_learner.generate_cloze import generate_cloze


def test_complete_word_does_not_replace_a_substring():
    assert generate_cloze("Put the carpet in the car.", "car") == "Put the carpet in the _____."
    with pytest.raises(ValueError):
        generate_cloze("Clean the carpet.", "car")


def test_inflection_and_first_occurrence():
    assert generate_cloze("I am running and enjoy running.", "running") == (
        "I am _________ and enjoy running."
    )


def test_phrase_and_escaped_punctuation():
    assert generate_cloze("Use the brake pedal.", "brake pedal") == "Use the _____________."
    assert generate_cloze("Use C++ today.", "C++") == "Use _____ today."


def test_blank_answer():
    with pytest.raises(ValueError):
        generate_cloze("Any sentence.", " ")


def test_case_insensitive_complete_answer():
    assert generate_cloze("The Boot is open.", "boot") == "The ______ is open."
    assert generate_cloze("Clean the CARPET, then use the Car.", "car") == (
        "Clean the CARPET, then use the _____."
    )
