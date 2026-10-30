# backend/tests/test_sense_reviews.py
# Insert and retrieve a review using temporary PostgreSQL tables, then roll back.
# Migration: backend/migrations/0001_create_sense_tables.sql

import os
from datetime import datetime
from pathlib import Path

import pytest

from lexical_learner.database import connect_database


def test_sense_review_insert_and_retrieve(monkeypatch: pytest.MonkeyPatch) -> None:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("Set DATABASE_URL to run the local PostgreSQL test")

    migration = (Path(__file__).parents[1] / "migrations/0001_create_sense_tables.sql").read_text()
    monkeypatch.setenv("PGHOSTADDR", "127.0.0.1")
    with connect_database() as connection:
        try:
            connection.execute(migration.replace("CREATE TABLE", "CREATE TEMP TABLE"))
            connection.execute(
                "INSERT INTO sense_reviews (sense_id, rating, review_type) VALUES (%s, %s, %s)",
                ("oewn-clutch__1.06.00..", 3, "manual"),
            )
            review = connection.execute(
                "SELECT id, sense_id, reviewed_at, rating, review_type FROM sense_reviews"
            ).fetchone()
            assert review is not None
            assert review[0] == 1
            assert review[1] == "oewn-clutch__1.06.00.."
            assert isinstance(review[2], datetime) and review[2].tzinfo is not None
            assert review[3:] == (3, "manual")
        finally:
            connection.rollback()
