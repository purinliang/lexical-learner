# backend/tests/test_select_senses.py
# Replay captured Gemini output and test invalid responses without network calls.
# I/O fixture: backend/tests/fixtures/select_senses_live.json

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from lexical_learner.select_senses import select_senses

RECORD = json.loads((Path(__file__).parent / "fixtures/select_senses_live.json").read_text())


@pytest.mark.parametrize(
    "response_text,error",
    [
        (json.dumps(RECORD["output"]), None),
        ("not JSON", json.JSONDecodeError),
        (
            json.dumps(
                {
                    ("wrong word" if word == "steering wheel" else word): indices
                    for word, indices in RECORD["output"].items()
                }
            ),
            ValueError,
        ),
        (json.dumps({**RECORD["output"], "steering wheel": [99]}), ValueError),
        (json.dumps({**RECORD["output"], "steering wheel": [0, 0]}), ValueError),
        (json.dumps({**RECORD["output"], "steering wheel": 0}), ValueError),
    ],
)
def test_select_senses(
    monkeypatch: pytest.MonkeyPatch, response_text: str, error: type[Exception] | None
) -> None:
    model = Mock()
    model.invoke.return_value = SimpleNamespace(text=response_text)
    factory = Mock(return_value=model)
    monkeypatch.setattr("lexical_learner.select_senses.create_model", factory)

    if error is None:
        assert select_senses(**RECORD["input"]) == RECORD["output"]
    else:
        with pytest.raises(error):
            select_senses(**RECORD["input"])

    factory.assert_called_once_with()
    model.invoke.assert_called_once()
    messages = model.invoke.call_args.args[0]
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    expected = f"Scenario: {RECORD['input']['prompt']}\nDefinitions: " + json.dumps(
        RECORD["input"]["definitions"], ensure_ascii=False, separators=(",", ":")
    )
    assert messages[1].content == expected


def test_select_senses_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Mock()
    monkeypatch.setattr("lexical_learner.select_senses.create_model", factory)
    assert select_senses("car parts", {}) == {}
    factory.assert_not_called()
