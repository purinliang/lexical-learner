# backend/tests/test_select_senses.py
# Adapt captured indices to the new contract and validate sense/taxonomy references offline.
# I/O fixture: backend/tests/fixtures/select_senses_live.json

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from lexical_learner.select_senses import select_senses

RECORD = json.loads((Path(__file__).parent / "fixtures/select_senses_live.json").read_text())

# Synthetic contract adaptation; the original real provider fixture is unchanged.
OUTPUT = {
    word: [{"index": index, "topic_ids": [], "subtopic_ids": []} for index in indices]
    for word, indices in RECORD["output"].items()
}


@pytest.mark.parametrize(
    "response_text,error",
    [
        (json.dumps(OUTPUT), None),
        ("not JSON", json.JSONDecodeError),
        (
            json.dumps(
                {
                    ("wrong word" if word == "steering wheel" else word): indices
                    for word, indices in OUTPUT.items()
                }
            ),
            ValueError,
        ),
        (
            json.dumps(
                {**OUTPUT, "steering wheel": [{"index": 99, "topic_ids": [], "subtopic_ids": []}]}
            ),
            ValueError,
        ),
        (
            json.dumps(
                {
                    **OUTPUT,
                    "steering wheel": [{"index": 0, "topic_ids": [], "subtopic_ids": []}] * 2,
                }
            ),
            ValueError,
        ),
        (json.dumps({**OUTPUT, "steering wheel": 0}), ValueError),
    ],
)
def test_select_senses(
    monkeypatch: pytest.MonkeyPatch, response_text: str, error: type[Exception] | None
) -> None:
    model = Mock()
    model.invoke.return_value = SimpleNamespace(text=response_text, response_metadata={})
    factory = Mock(return_value=model)
    monkeypatch.setattr("lexical_learner.select_senses.create_model", factory)

    if error is None:
        assert select_senses(**RECORD["input"], taxonomy=[]) == OUTPUT
    else:
        with pytest.raises(error):
            select_senses(**RECORD["input"], taxonomy=[])

    factory.assert_called_once_with()
    model.invoke.assert_called_once()
    messages = model.invoke.call_args.args[0]
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert json.loads(messages[1].content) == {
        "scenario": RECORD["input"]["prompt"],
        "definitions": RECORD["input"]["definitions"],
        "topics": [],
    }


def test_select_senses_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Mock()
    monkeypatch.setattr("lexical_learner.select_senses.create_model", factory)
    assert select_senses("car parts", {}, []) == {}
    factory.assert_not_called()


TAXONOMY = [
    {
        "id": "life",
        "name": "Life",
        "description": "Daily life.",
        "topics": [
            {
                "id": "food-drink",
                "name": "Food & Drink",
                "description": "Food and cooking.",
                "subtopics": [
                    {"id": "food-cooking", "name": "Cooking", "description": "Food preparation."},
                    {
                        "id": "food-ingredients",
                        "name": "Ingredients",
                        "description": "Ingredients.",
                    },
                ],
            },
            {
                "id": "home-living",
                "name": "Home & Living",
                "description": "Home maintenance.",
                "subtopics": [],
            },
        ],
    }
]


def test_contextual_sense_can_link_to_multiple_subtopics(monkeypatch):
    output = {
        "score": [
            {
                "index": 1,
                "topic_ids": ["food-drink"],
                "subtopic_ids": ["food-cooking", "food-ingredients"],
            }
        ]
    }
    model = Mock()
    model.invoke.return_value = SimpleNamespace(text=json.dumps(output), response_metadata={})
    monkeypatch.setattr("lexical_learner.select_senses.create_model", Mock(return_value=model))
    assert (
        select_senses(
            "Score chicken wings before marinating.",
            {"score": ["A number of points.", "Make shallow cuts in a surface."]},
            TAXONOMY,
        )
        == output
    )


@pytest.mark.parametrize(
    "topics,subtopics",
    [
        (["invented-topic"], []),
        (["food-drink"], ["invented-subtopic"]),
        (["food-drink", "food-drink"], []),
        (["food-drink"], ["food-cooking", "food-cooking"]),
        ([], ["food-cooking"]),
        (["home-living"], ["food-cooking"]),
    ],
)
def test_invalid_taxonomy_links_are_rejected(monkeypatch, topics, subtopics):
    model = Mock()
    model.invoke.return_value = SimpleNamespace(
        text=json.dumps({"score": [{"index": 0, "topic_ids": topics, "subtopic_ids": subtopics}]}),
        response_metadata={},
    )
    monkeypatch.setattr("lexical_learner.select_senses.create_model", Mock(return_value=model))
    with pytest.raises(ValueError):
        select_senses("Score the chicken.", {"score": ["Make cuts."]}, TAXONOMY)
