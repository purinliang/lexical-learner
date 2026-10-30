# backend/src/lexical_learner/lookup_words.py
# Look up WordNet senses, definitions and examples offline for a list of words.
# I/O fixture: backend/tests/fixtures/lookup_words.json

from typing import TypedDict

import wn


class WordSense(TypedDict):
    sense_id: str
    definition: list[str]
    examples: list[str]


def lookup_words(words: list[str]) -> dict[str, list[WordSense]]:
    dictionary = wn.Wordnet("oewn:2025")
    results: dict[str, list[WordSense]] = {}
    for word in words:
        results[word] = []
        if not word.strip():
            continue
        for sense in dictionary.senses(word.strip()):
            synset = sense.synset()
            results[word].append(
                {
                    "sense_id": sense.id,
                    "definition": synset.definitions(),
                    "examples": sense.examples() + synset.examples(),
                }
            )
    return results
