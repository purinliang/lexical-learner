# backend/src/lexical_learner/generate_lesson.py
# Select WordNet senses, then reuse or generate their persisted exercise content.
# I/O fixture: backend/tests/fixtures/generate_lesson_live.json

from lexical_learner.ensure_sense_content import LessonSense, ensure_sense_content
from lexical_learner.generate_vocabulary import generate_vocabulary
from lexical_learner.lookup_words import lookup_words
from lexical_learner.select_senses import select_senses


def generate_lesson(prompt: str) -> dict[str, list[LessonSense]]:
    words = generate_vocabulary(prompt)
    if not words:
        return {}

    senses = lookup_words(words)
    definitions = {
        word: ["; ".join(sense["definition"]) for sense in entries]
        for word, entries in senses.items()
    }
    selected = select_senses(prompt, definitions)
    lesson = {
        word: [senses[word][index] for index in indices] for word, indices in selected.items()
    }
    return ensure_sense_content(lesson, language="zh", source="gemini")
