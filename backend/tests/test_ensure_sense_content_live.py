# backend/tests/test_ensure_sense_content_live.py
# Call Gemini once for one previously selected sense, with database I/O mocked.
# Input fixture: backend/tests/fixtures/generate_lesson_live.json

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from unittest.mock import MagicMock, Mock

import pytest

from lexical_learner.ensure_sense_content import ensure_sense_content
from lexical_learner.generate_cloze import generate_cloze
from lexical_learner.llm import create_model

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.live
def test_ensure_sense_content_live(monkeypatch, request):
    if request.config.option.markexpr != "live":
        pytest.skip('Explicitly select live tests with -m live -o addopts=""')

    recorded = json.loads((FIXTURES / "generate_lesson_live.json").read_text())
    lesson = {"clutch": recorded["output"]["clutch"][:1]}
    connection = MagicMock()
    connection.execute.return_value.fetchall.return_value = []
    connection.execute.return_value.fetchone.return_value = (1,)
    connection.__enter__.return_value = connection
    monkeypatch.setattr(
        "lexical_learner.ensure_sense_content.connect_database", Mock(return_value=connection)
    )
    model = Mock(wraps=create_model())
    monkeypatch.setattr(
        "lexical_learner.ensure_sense_content.create_model", Mock(return_value=model)
    )

    started = perf_counter()
    result = ensure_sense_content(lesson, language="zh", source="gemini")
    elapsed_seconds = round(perf_counter() - started, 3)
    print(json.dumps({"elapsed_seconds": elapsed_seconds}))
    model.invoke.assert_called_once()
    sense = result["clutch"][0]
    assert sense["sense_id"] == lesson["clutch"][0]["sense_id"]
    assert sense["translation"] is not None
    assert sense["translation"]["translation"].strip()
    assert len(sense["clozes"]) == 1
    cloze = sense["clozes"][0]
    question = generate_cloze(cloze["sentence"], cloze["answer"])
    assert question != cloze["sentence"]
    assert "_" * (len(cloze["answer"]) + 2) in question

    capture = {
        "provider": "Google",
        "model": os.environ["GOOGLE_MODEL"],
        "captured_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": elapsed_seconds,
        "input_fixture": "generate_lesson_live.json",
        "database": "mock",
        "input": {"lesson": lesson, "language": "zh", "source": "gemini"},
        "output": result,
        "question": question,
    }
    print(json.dumps(capture, ensure_ascii=False, indent=2))
    capture_path = FIXTURES / "ensure_sense_content_live.json"
    if not capture_path.exists():
        capture_path.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n")
