# backend/tests/test_generate_lesson.py
# Test selected-sense assembly and content handoff using replayed Gemini outputs.
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
    selections = {
        word: [{"index": index, "topic_ids": [], "subtopic_ids": []} for index in indices]
        for word, indices in selection_record["output"].items()
    }
    select = Mock(return_value=selections)
    monkeypatch.setattr(
        "lexical_learner.generate_lesson.get_taxonomy", Mock(invoke=Mock(return_value=[]))
    )
    monkeypatch.setattr("lexical_learner.generate_lesson.generate_vocabulary", generate)
    monkeypatch.setattr("lexical_learner.generate_lesson.select_senses", select)
    enrich = Mock(side_effect=lambda lesson, **kwargs: lesson)
    monkeypatch.setattr("lexical_learner.generate_lesson.ensure_sense_content", enrich)

    lesson = generate_lesson(**lesson_record["input"])
    expected = {
        word: [{**sense, "topics": [], "subtopics": []} for sense in senses]
        for word, senses in lesson_record["output"].items()
    }
    assert lesson == expected
    assert len(lesson["clutch"]) == 2
    assert lesson["gear shift"] == []
    assert "boot" in lesson["trunk"][0]["synonyms"]
    assert "trunk" not in lesson["trunk"][0]["synonyms"]
    assert lesson["clutch"][0]["synonyms"] == ["clutch pedal"]
    assert lesson["clutch"][1]["synonyms"] == []
    enrich.assert_called_once_with(lesson_record["output"], language="zh", source="gemini")
    generate.assert_called_once_with(lesson_record["input"]["prompt"])
    select.assert_called_once()
    prompt, definitions, taxonomy = select.call_args.args
    assert prompt == selection_record["input"]["prompt"]
    assert taxonomy == []
    # Historical phrase lookups stay unchanged; new component lookups are additional.
    assert {word: definitions[word] for word in selection_record["input"]["definitions"]} == (
        selection_record["input"]["definitions"]
    )
    assert definitions["gear shift"] == []
    assert definitions["gear"]
    assert definitions["shift"]


def test_generate_lesson_stops_for_overlong_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    model = Mock()
    lookup = Mock()
    select = Mock()
    enrich = Mock()
    monkeypatch.setattr("lexical_learner.generate_vocabulary.create_model", model)
    monkeypatch.setattr("lexical_learner.generate_lesson.lookup_words", lookup)
    monkeypatch.setattr("lexical_learner.generate_lesson.select_senses", select)
    monkeypatch.setattr("lexical_learner.generate_lesson.ensure_sense_content", enrich)

    assert generate_lesson("车" * 342) == {}
    model.assert_not_called()
    lookup.assert_not_called()
    select.assert_not_called()
    enrich.assert_not_called()
