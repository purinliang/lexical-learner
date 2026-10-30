# backend/tests/test_lookup_words.py
# Test offline batch lookup, multiple senses and unmatched inputs.
# I/O fixture: backend/tests/fixtures/lookup_words.json

import wn

from lexical_learner.lookup_words import lookup_words


def test_lookup_words_preserves_multiple_senses() -> None:
    results = lookup_words(["boot", "steering wheel"])
    dictionary = wn.Wordnet("oewn:2025")

    assert set(results) == {"boot", "steering wheel"}
    assert len(results["boot"]) > 1
    assert results["steering wheel"]
    definitions = [text for result in results["boot"] for text in result["definition"]]
    assert any("footwear" in text for text in definitions)
    assert any("compartment in an automobile" in text for text in definitions)
    for word, senses in results.items():
        assert {result["sense_id"] for result in senses} == {
            sense.id for sense in dictionary.senses(word)
        }
        for result in senses:
            assert set(result) == {"sense_id", "definition", "examples"}
            sense = dictionary.sense(result["sense_id"])
            assert result["definition"] == sense.synset().definitions()
            assert result["examples"] == sense.examples() + sense.synset().examples()


def test_lookup_words_missing_or_empty() -> None:
    assert lookup_words(["quuxzzlearnernonword", "boot quuxzzlearnernonword", "   "]) == {
        "quuxzzlearnernonword": [],
        "boot quuxzzlearnernonword": [],
        "   ": [],
    }
    assert lookup_words([]) == {}
