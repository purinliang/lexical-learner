# backend/src/lexical_learner/generate_lesson.py
# Generate vocabulary, look up senses and map Gemini selections to dictionary entries.
# I/O fixture: backend/tests/fixtures/generate_lesson_live.json

from lexical_learner.generate_vocabulary import generate_vocabulary
from lexical_learner.lookup_words import WordSense, lookup_words
from lexical_learner.select_senses import select_senses


def generate_lesson(prompt: str) -> dict[str, list[WordSense]]:
    words = generate_vocabulary(prompt)
    if not words:
        return {}

    senses = lookup_words(words)
    definitions = {
        word: ["; ".join(sense["definition"]) for sense in entries]
        for word, entries in senses.items()
    }
    selected = select_senses(prompt, definitions)
    return {word: [senses[word][index] for index in indices] for word, indices in selected.items()}
