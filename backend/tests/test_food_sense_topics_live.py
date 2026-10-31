# backend/tests/test_food_sense_topics_live.py
# Evaluate real Gemini vocabulary/sense/topic selection without creating taxonomy or clozes.
# Captures: backend/tests/fixtures/sense_topics/

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pytest

from lexical_learner.generate_vocabulary import generate_vocabulary
from lexical_learner.get_taxonomy import get_taxonomy
from lexical_learner.lookup_words import lookup_words
from lexical_learner.select_senses import select_senses


@pytest.mark.live
@pytest.mark.parametrize(
    "scenario,prompt",
    [
        (
            "creamy_seafood_pasta",
            "我发现奶油海鲜意大利面加点黑胡椒和欧芹特别漂亮，只不过如何控制火候不要让意大利面太软或者太硬需要一些经验。",
        ),
        (
            "air_fryer_chicken_wings",
            "在鸡翅表面上划两刀，可以加速腌制的速度，后续使用空气炸锅炸鸡翅的时候也更容易熟得均匀。",
        ),
    ],
)
def test_food_sense_topics_live(request, scenario, prompt):
    if request.config.option.markexpr != "live":
        pytest.skip('Explicitly select live tests with -m live -o addopts=""')
    folder = Path(__file__).parent / "fixtures/sense_topics" / scenario
    folder.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid4())

    def record(stage, inputs, operation):
        captured = {
            "run_id": run_id,
            "stage": stage,
            "model": os.environ["GOOGLE_MODEL"],
            "captured_at": datetime.now(UTC).isoformat(),
            "input": inputs,
        }
        print(f"[{scenario}] {stage} started", flush=True)
        started = perf_counter()
        try:
            output = operation()
            captured["output"] = output
            return output
        except Exception as error:
            captured["error"] = {"type": type(error).__name__}
            raise
        finally:
            captured["elapsed_seconds"] = round(perf_counter() - started, 3)
            (folder / f"{stage}.json").write_text(
                json.dumps(captured, ensure_ascii=False, indent=2) + "\n"
            )
            print(f"[{scenario}] {stage}: {captured['elapsed_seconds']}s", flush=True)

    taxonomy = record("taxonomy", {}, lambda: get_taxonomy.invoke({}))
    words = record("generate_vocabulary", {"prompt": prompt}, lambda: generate_vocabulary(prompt))
    assert 1 <= len(words) <= 30
    senses = record("lookup_words", {"words": words}, lambda: lookup_words(words))
    definitions = {
        word: ["; ".join(sense["definition"]) for sense in entries]
        for word, entries in senses.items()
    }
    selected = record(
        "select_senses",
        {"prompt": prompt, "definitions": definitions, "taxonomy": taxonomy},
        lambda: select_senses(prompt, definitions, taxonomy),
    )
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
    lesson = {
        word: [
            {
                **senses[word][entry["index"]],
                "topics": [topic_refs[ref] for ref in entry["topic_ids"]],
                "subtopics": [subtopic_refs[ref] for ref in entry["subtopic_ids"]],
            }
            for entry in entries
        ]
        for word, entries in selected.items()
    }
    record("linked_senses", {"selected": selected}, lambda: lesson)
    assert any(lesson.values())
    assert get_taxonomy.invoke({}) == taxonomy, "Sense selection must not change taxonomy"
    summary = {
        "scenario": scenario,
        "candidate_count": len(words),
        "selected_words": sum(bool(entries) for entries in lesson.values()),
        "selected_senses": sum(len(entries) for entries in lesson.values()),
        "not_found": [word for word, entries in senses.items() if not entries],
        "no_matching_sense": [
            word for word, entries in selected.items() if senses[word] and not entries
        ],
    }
    record("summary", {}, lambda: summary)
    print(json.dumps({"summary": summary, "lesson": lesson}, ensure_ascii=False, indent=2))
