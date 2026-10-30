# backend/tests/test_ensure_sense_content.py
# Test cached and missing content with mocked PostgreSQL and Gemini boundaries.
# Synthetic fixture: backend/tests/fixtures/sense_content_synthetic.json

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from lexical_learner.ensure_sense_content import ensure_sense_content
from lexical_learner.lookup_words import WordSense

RECORD = json.loads((Path(__file__).parent / "fixtures/sense_content_synthetic.json").read_text())
SENSE: WordSense = {
    "sense_id": "oewn-clutch__1.06.00..",
    "definition": RECORD["input"]["0"]["definitions"],
    "examples": ["A WordNet example must not become a cached exercise."],
    "synonyms": ["clutch pedal"],
}


def boundaries(monkeypatch, translations=(), clozes=(), output=None):
    connection = Mock()
    factory = Mock()
    factory.return_value.__enter__ = Mock(return_value=connection)
    factory.return_value.__exit__ = Mock(return_value=False)
    connection.execute.side_effect = lambda sql, params: Mock(
        fetchall=Mock(return_value=translations if "sense_translations" in sql else clozes),
        fetchone=Mock(return_value=(8,)),
    )
    model = Mock()
    model.invoke.return_value = SimpleNamespace(
        text=json.dumps(output if output is not None else RECORD["output"])
    )

    def invoke(*args, **kwargs):
        assert factory.call_count == 1
        assert factory.return_value.__exit__.call_count == 1
        return model.invoke.return_value

    model.invoke.side_effect = invoke
    create = Mock(return_value=model)
    monkeypatch.setattr("lexical_learner.ensure_sense_content.connect_database", factory)
    monkeypatch.setattr("lexical_learner.ensure_sense_content.create_model", create)
    return connection, create, model


def saved_cloze(sense_id):
    return (sense_id, 7, "Use the clutch.", "clutch", "previous-source")


def test_complete_content_skips_gemini(monkeypatch):
    sense_id = SENSE["sense_id"]
    connection, create, _ = boundaries(
        monkeypatch, [(sense_id, "已有释义", "previous-source")], [saved_cloze(sense_id)]
    )
    lesson = {"clutch": [deepcopy(SENSE)]}
    original = deepcopy(lesson)
    result = ensure_sense_content(lesson, language="zh", source="gemini")
    assert lesson == original
    assert result["clutch"][0]["translation"] == {
        "language": "zh",
        "translation": "已有释义",
        "source": "previous-source",
    }
    assert result["clutch"][0]["clozes"][0]["id"] == 7
    assert result["clutch"][0]["clozes"][0]["source"] == "previous-source"
    assert result["clutch"][0]["examples"] == SENSE["examples"]
    create.assert_not_called()
    assert connection.execute.call_count == 2


def test_multiple_incomplete_senses_use_one_call_and_only_missing_fields(monkeypatch):
    other: WordSense = {**SENSE, "sense_id": "synthetic-other-sense"}
    complete: WordSense = {**SENSE, "sense_id": "synthetic-complete-sense"}
    output = {
        "0": {"translation": "新翻译"},
        "1": {"cloze": RECORD["output"]["0"]["cloze"]},
    }
    connection, create, model = boundaries(
        monkeypatch,
        [(other["sense_id"], "保留翻译", "old"), (complete["sense_id"], "完整翻译", "old")],
        [saved_cloze(SENSE["sense_id"]), saved_cloze(complete["sense_id"])],
        output,
    )
    result = ensure_sense_content(
        {"clutch": [SENSE, other, complete]}, language="zh", source="gemini"
    )["clutch"]
    create.assert_called_once_with()
    model.invoke.assert_called_once()
    payload = json.loads(model.invoke.call_args.args[0][1].content)
    assert payload == {
        "0": {"word": "clutch", "definitions": SENSE["definition"], "missing": ["translation"]},
        "1": {"word": "clutch", "definitions": other["definition"], "missing": ["cloze"]},
    }
    assert result[0]["translation"]["translation"] == "新翻译"
    assert result[0]["clozes"][0]["id"] == 7
    assert result[1]["translation"]["translation"] == "保留翻译"
    assert result[1]["clozes"][0]["id"] == 8
    assert result[2]["translation"]["translation"] == "完整翻译"
    inserts = [(call.args[0], call.args[1]) for call in connection.execute.call_args_list[2:]]
    assert len(inserts) == 2
    assert inserts[0][1] == (SENSE["sense_id"], "zh", "新翻译", "gemini")
    cloze = RECORD["output"]["0"]["cloze"]
    assert inserts[1][1] == (
        other["sense_id"],
        cloze["sentence"],
        "clutch",
        "gemini",
    )
    assert all(sql.startswith("INSERT INTO") for sql, _ in inserts)


def test_empty_cache_generates_both_fields(monkeypatch):
    connection, _, model = boundaries(monkeypatch)
    result = ensure_sense_content({"clutch": [SENSE]}, language="zh", source="gemini")["clutch"][0]
    assert json.loads(model.invoke.call_args.args[0][1].content) == RECORD["input"]
    assert result["translation"]["translation"] == RECORD["output"]["0"]["translation"]
    cloze = result["clozes"][0]
    assert cloze["sentence"] == RECORD["output"]["0"]["cloze"]["sentence"]
    assert "question" not in cloze
    assert cloze["source"] == "gemini"
    assert connection.execute.call_count == 4


def test_partial_invalid_content_rejects_entire_batch_without_retry(monkeypatch):
    connection, _, model = boundaries(
        monkeypatch,
        output={
            "0": {
                "translation": "离合器",
                "cloze": {"sentence": "No answer here.", "answer": "clutch"},
            }
        },
    )
    with pytest.raises(ValueError):
        ensure_sense_content({"clutch": [SENSE]}, language="zh", source="gemini")
    assert connection.execute.call_count == 2
    model.invoke.assert_called_once()


def test_inflected_answer_is_saved_without_rendering(monkeypatch):
    connection, _, _ = boundaries(
        monkeypatch,
        output={
            "0": {
                "translation": "跑步",
                "cloze": {"sentence": "I am running and enjoy running.", "answer": "running"},
            }
        },
    )
    result = ensure_sense_content({"run": [SENSE]}, language="zh", source="gemini")["run"][0]
    cloze = result["clozes"][0]
    assert cloze["answer"] == "running"
    assert "question" not in cloze
    assert connection.execute.call_args.args[1] == (
        SENSE["sense_id"],
        "I am running and enjoy running.",
        "running",
        "gemini",
    )


def test_missing_response_is_rejected(monkeypatch):
    connection, _, model = boundaries(monkeypatch, output={})
    with pytest.raises(ValueError):
        ensure_sense_content({"clutch": [SENSE]}, language="zh", source="gemini")
    assert connection.execute.call_count == 2
    model.invoke.assert_called_once()


def test_answer_inside_another_word_is_not_saved(monkeypatch):
    connection, _, _ = boundaries(
        monkeypatch,
        output={
            "0": {
                "translation": "汽车",
                "cloze": {"sentence": "Clean the carpet.", "answer": "car"},
            }
        },
    )
    with pytest.raises(ValueError):
        ensure_sense_content({"car": [SENSE]}, language="zh", source="gemini")
    assert connection.execute.call_count == 2


def test_invalid_json_propagates_without_inserts(monkeypatch):
    connection, _, model = boundaries(monkeypatch)
    model.invoke.return_value.text = "not JSON"
    with pytest.raises(json.JSONDecodeError):
        ensure_sense_content({"clutch": [SENSE]}, language="zh", source="gemini")
    assert connection.execute.call_count == 2
    model.invoke.assert_called_once()


def test_empty_lesson_skips_database_and_gemini(monkeypatch):
    connection, create, _ = boundaries(monkeypatch)
    assert ensure_sense_content({"missing": []}, language="zh", source="gemini") == {"missing": []}
    connection.execute.assert_not_called()
    create.assert_not_called()


@pytest.mark.parametrize(
    "output",
    [
        {"wrong": RECORD["output"]["0"]},
        {"0": None},
        {"0": {"translation": "Incomplete"}},
        {"0": {"translation": " ", "cloze": RECORD["output"]["0"]["cloze"]}},
        {"0": {"translation": "Valid", "cloze": {"sentence": 1, "answer": "car"}}},
        {"0": {"translation": "Valid", "cloze": {"sentence": "A car."}}},
        {"0": {**RECORD["output"]["0"], "unexpected": "field"}},
    ],
)
def test_invalid_structure_never_opens_write_connection(monkeypatch, output):
    connection, _, model = boundaries(monkeypatch, output=output)
    with pytest.raises(ValueError):
        ensure_sense_content({"clutch": [SENSE]}, language="zh", source="gemini")
    assert connection.execute.call_count == 2
    model.invoke.assert_called_once()


def test_invalid_later_sense_prevents_all_writes(monkeypatch):
    other: WordSense = {**SENSE, "sense_id": "synthetic-other-sense"}
    connection, _, _ = boundaries(
        monkeypatch,
        output={
            "0": RECORD["output"]["0"],
            "1": {"translation": "Valid", "cloze": {"sentence": "A carpet.", "answer": "car"}},
        },
    )
    with pytest.raises(ValueError):
        ensure_sense_content({"clutch": [SENSE, other]}, language="zh", source="gemini")
    assert connection.execute.call_count == 2


def test_missing_reference_prevents_all_writes(monkeypatch):
    other: WordSense = {**SENSE, "sense_id": "synthetic-other-sense"}
    connection, _, _ = boundaries(monkeypatch, output=RECORD["output"])
    with pytest.raises(ValueError):
        ensure_sense_content({"clutch": [SENSE, other]}, language="zh", source="gemini")
    assert connection.execute.call_count == 2
