# backend/tests/test_sense_content_database.py
# Exercise the workflow with local PostgreSQL temporary tables and mocked Gemini.
# Synthetic fixture: backend/tests/fixtures/sense_content_synthetic.json

import json
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from lexical_learner.database import connect_database
from lexical_learner.generate_lesson import generate_lesson


def test_workflow_persists_content_and_reuses_it(monkeypatch):
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("Set DATABASE_URL to run the local PostgreSQL test")

    fixture = json.loads(
        (Path(__file__).parent / "fixtures/sense_content_synthetic.json").read_text()
    )
    migration = (Path(__file__).parents[1] / "migrations/0001_create_sense_tables.sql").read_text()
    sense = {
        "sense_id": "oewn-clutch__1.06.00..",
        "definition": fixture["input"]["0"]["definitions"],
        "examples": ["This WordNet example must not be persisted."],
        "synonyms": ["clutch pedal"],
    }
    monkeypatch.setattr(
        "lexical_learner.generate_lesson.generate_vocabulary", Mock(return_value=["clutch"])
    )
    monkeypatch.setattr(
        "lexical_learner.generate_lesson.lookup_words", Mock(return_value={"clutch": [sense]})
    )
    monkeypatch.setattr(
        "lexical_learner.generate_lesson.select_senses", Mock(return_value={"clutch": [0]})
    )
    model = Mock()
    model.invoke.return_value = SimpleNamespace(text=json.dumps(fixture["output"]))
    monkeypatch.setattr(
        "lexical_learner.ensure_sense_content.create_model", Mock(return_value=model)
    )

    monkeypatch.setenv("PGHOSTADDR", "127.0.0.1")
    with connect_database() as connection:
        try:
            connection.execute(migration.replace("CREATE TABLE", "CREATE TEMP TABLE"))

            @contextmanager
            def use_test_transaction():
                yield connection

            monkeypatch.setattr(
                "lexical_learner.ensure_sense_content.connect_database", use_test_transaction
            )
            first = generate_lesson("Car parts")
            second = generate_lesson("Car parts")
            assert first == second
            model.invoke.assert_called_once()
            content = first["clutch"][0]
            assert content["translation"] == {
                "language": "zh",
                "translation": fixture["output"]["0"]["translation"],
                "source": "gemini",
            }
            cloze = content["clozes"][0]
            assert cloze["sentence"] == fixture["output"]["0"]["cloze"]["sentence"]
            assert "question" not in cloze
            assert connection.execute("SELECT count(*) FROM sense_translations").fetchone() == (1,)
            assert connection.execute("SELECT count(*) FROM sense_clozes").fetchone() == (1,)
            assert connection.execute("SELECT count(*) FROM sense_reviews").fetchone() == (0,)
        finally:
            connection.rollback()
