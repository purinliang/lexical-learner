# backend/tests/test_get_taxonomy.py
# Test the read-only taxonomy tool with mocked rows and temporary PostgreSQL tables.

import os
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest

from lexical_learner.database import connect_database
from lexical_learner.get_taxonomy import get_taxonomy

EXPECTED = [
    {
        "id": "test-category",
        "name": "Test Category",
        "description": "A test category.",
        "topics": [
            {
                "id": "topic-a",
                "name": "Topic A",
                "description": "First test topic.",
                "subtopics": [],
            },
            {
                "id": "topic-b",
                "name": "Topic B",
                "description": "Second test topic.",
                "subtopics": [],
            },
        ],
    }
]


def test_taxonomy_tool_returns_tree_and_same_named_subtopics(monkeypatch):
    category = EXPECTED[0]
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.side_effect = [
        MagicMock(fetchall=lambda: [(category["id"], category["name"], category["description"])]),
        MagicMock(
            fetchall=lambda: [
                (topic["id"], category["id"], topic["name"], topic["description"])
                for topic in category["topics"]
            ]
        ),
        MagicMock(
            fetchall=lambda: [
                ("subtopic-a", "topic-a", "Shopping", "First test subtopic."),
                ("subtopic-b", "topic-b", "Shopping", "Second test subtopic."),
            ]
        ),
    ]
    monkeypatch.setattr("lexical_learner.get_taxonomy.connect_database", lambda: connection)
    expected = deepcopy(EXPECTED)
    expected[0]["topics"][0]["subtopics"] = [
        {"id": "subtopic-a", "name": "Shopping", "description": "First test subtopic."}
    ]
    expected[0]["topics"][1]["subtopics"] = [
        {"id": "subtopic-b", "name": "Shopping", "description": "Second test subtopic."}
    ]
    assert get_taxonomy.invoke({}) == expected
    assert get_taxonomy.args == {}
    assert all(call.args[0].startswith("SELECT") for call in connection.execute.call_args_list)


def test_empty_taxonomy(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchall.return_value = []
    monkeypatch.setattr("lexical_learner.get_taxonomy.connect_database", lambda: connection)
    assert get_taxonomy.invoke({}) == []


def test_taxonomy_database_tree_and_constraints(monkeypatch):
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("Set DATABASE_URL to run the local PostgreSQL test")
    monkeypatch.setenv("PGHOSTADDR", "127.0.0.1")
    migrations = Path(__file__).parents[1] / "migrations"
    with connect_database() as connection:
        try:
            connection.execute(
                (migrations / "0002_create_taxonomy.sql")
                .read_text()
                .replace("CREATE TABLE", "CREATE TEMP TABLE")
            )
            for category in EXPECTED:
                connection.execute(
                    "INSERT INTO categories (id, name, description) VALUES (%s, %s, %s)",
                    (category["id"], category["name"], category["description"]),
                )
                for topic in category["topics"]:
                    connection.execute(
                        "INSERT INTO topics (id, category_id, name, description) "
                        "VALUES (%s, %s, %s, %s)",
                        (topic["id"], category["id"], topic["name"], topic["description"]),
                    )
            # The wrapper avoids closing this test's transaction after the read-only tool call.
            context = MagicMock()
            context.__enter__.return_value = connection
            monkeypatch.setattr("lexical_learner.get_taxonomy.connect_database", lambda: context)
            assert get_taxonomy.invoke({}) == EXPECTED
            connection.execute(
                "INSERT INTO subtopics (id, topic_id, name, description) VALUES "
                "('subtopic-a', 'topic-a', 'Shopping', 'First test subtopic.'), "
                "('subtopic-b', 'topic-b', 'Shopping', 'Second test subtopic.')"
            )
            for statement, error in [
                (
                    "INSERT INTO categories VALUES ('missing-description', 'Missing', NULL)",
                    psycopg.errors.NotNullViolation,
                ),
                (
                    "INSERT INTO topics VALUES ('missing', 'test-category', 'Missing', NULL)",
                    psycopg.errors.NotNullViolation,
                ),
                (
                    "INSERT INTO subtopics VALUES ('missing', 'topic-a', 'Missing', NULL)",
                    psycopg.errors.NotNullViolation,
                ),
                (
                    "INSERT INTO topics VALUES ('duplicate', 'test-category', 'Topic B', 'Copy')",
                    psycopg.errors.UniqueViolation,
                ),
                (
                    "INSERT INTO subtopics VALUES ('duplicate', 'topic-a', 'Shopping', 'Copy')",
                    psycopg.errors.UniqueViolation,
                ),
                (
                    "INSERT INTO topics VALUES ('orphan', 'missing', 'Orphan', 'Missing parent')",
                    psycopg.errors.ForeignKeyViolation,
                ),
                (
                    "INSERT INTO subtopics VALUES ('orphan', 'missing', 'Orphan', 'Orphan')",
                    psycopg.errors.ForeignKeyViolation,
                ),
            ]:
                with pytest.raises(error), connection.transaction():
                    connection.execute(statement)
        finally:
            connection.rollback()
