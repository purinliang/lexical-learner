# backend/src/lexical_learner/lookup_words.py
# Look up words offline, splitting unmatched phrases into independent word lookups.
# I/O fixture: backend/tests/fixtures/lookup_words.json

from typing import TypedDict

import wn


class WordSense(TypedDict):
    sense_id: str
    definition: list[str]
    examples: list[str]
    synonyms: list[str]


def lookup_words(words: list[str]) -> dict[str, list[WordSense]]:
    dictionary = wn.Wordnet("oewn:2025")
    results: dict[str, list[WordSense]] = {}
    pending = list(dict.fromkeys(words))
    seen = set(pending)
    for word in pending:
        results[word] = []
        if not word.strip():
            continue
        for sense in dictionary.senses(word.strip()):
            synset = sense.synset()
            lemma = sense.word().lemma()
            results[word].append(
                {
                    "sense_id": sense.id,
                    "definition": synset.definitions(),
                    "examples": sense.examples() + synset.examples(),
                    "synonyms": [
                        synonym
                        for synonym in synset.lemmas()
                        if synonym.casefold() != lemma.casefold()
                    ],
                }
            )
        # Keep the unmatched phrase empty; component senses do not verify the phrase.
        if not results[word] and len(parts := word.split()) > 1:
            for part in parts:
                if part not in seen:
                    seen.add(part)
                    pending.append(part)
    return results
