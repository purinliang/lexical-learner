# backend/tests/test_generate_lesson.py
# Test local assembly using real WordNet data and replayed Gemini outputs.
# I/O fixture: backend/tests/fixtures/generate_lesson_live.json

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from lexical_learner.generate_lesson import generate_lesson

FIXTURES = Path(__file__).parent / "fixtures"


def test_generate_lesson(monkeypatch: pytest.MonkeyPatch) -> None:
    vocabulary_record = json.loads((FIXTURES / "generate_vocabulary_live.json").read_text())
    selection_record = json.loads((FIXTURES / "select_senses_live.json").read_text())
    lesson_record = json.loads((FIXTURES / "generate_lesson_live.json").read_text())
    generate = Mock(return_value=vocabulary_record["output"])
    select = Mock(return_value=selection_record["output"])
    monkeypatch.setattr("lexical_learner.generate_lesson.generate_vocabulary", generate)
    monkeypatch.setattr("lexical_learner.generate_lesson.select_senses", select)

    lesson = generate_lesson(**lesson_record["input"])
    assert lesson == lesson_record["output"]
    assert len(lesson["clutch"]) == 2
    assert lesson["gear shift"] == []
    generate.assert_called_once_with(lesson_record["input"]["prompt"])
    select.assert_called_once_with(
        selection_record["input"]["prompt"], selection_record["input"]["definitions"]
    )


def test_generate_lesson_stops_for_overlong_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    model = Mock()
    lookup = Mock()
    select = Mock()
    monkeypatch.setattr("lexical_learner.generate_vocabulary.create_model", model)
    monkeypatch.setattr("lexical_learner.generate_lesson.lookup_words", lookup)
    monkeypatch.setattr("lexical_learner.generate_lesson.select_senses", select)

    assert generate_lesson("车" * 342) == {}
    model.assert_not_called()
    lookup.assert_not_called()
    select.assert_not_called()
