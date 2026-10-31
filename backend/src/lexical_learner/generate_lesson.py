# backend/src/lexical_learner/generate_lesson.py
# Select WordNet senses, then reuse or generate their persisted exercise content.
# I/O fixture: backend/tests/fixtures/generate_lesson_live.json

from lexical_learner.ensure_sense_content import LessonSense, ensure_sense_content
from lexical_learner.generate_vocabulary import generate_vocabulary
from lexical_learner.get_taxonomy import get_taxonomy
from lexical_learner.lookup_words import lookup_words
from lexical_learner.select_senses import select_senses


class ClassifiedSense(LessonSense):
    topics: list[dict[str, str]]
    subtopics: list[dict[str, str]]


def generate_lesson(prompt: str) -> dict[str, list[ClassifiedSense]]:
    words = generate_vocabulary(prompt)
    if not words:
        return {}

    senses = lookup_words(words)
    definitions = {
        word: ["; ".join(sense["definition"]) for sense in entries]
        for word, entries in senses.items()
    }
    taxonomy = get_taxonomy.invoke({})
    selected = select_senses(prompt, definitions, taxonomy)
    lesson = {
        word: [senses[word][entry["index"]] for entry in entries]
        for word, entries in selected.items()
    }
    enriched = ensure_sense_content(lesson, language="zh", source="gemini")
    topic_refs = {
        topic["id"]: {"id": topic["id"], "name": topic["name"], "category": category["name"]}
        for category in taxonomy
        for topic in category["topics"]
    }
    subtopic_refs = {
        subtopic["id"]: {"id": subtopic["id"], "name": subtopic["name"], "topic_id": topic["id"]}
        for category in taxonomy
        for topic in category["topics"]
        for subtopic in topic["subtopics"]
    }
    return {
        word: [
            ClassifiedSense(
                **sense,
                topics=[topic_refs[ref] for ref in entry["topic_ids"]],
                subtopics=[subtopic_refs[ref] for ref in entry["subtopic_ids"]],
            )
            for sense, entry in zip(enriched[word], entries, strict=True)
        ]
        for word, entries in selected.items()
    }
