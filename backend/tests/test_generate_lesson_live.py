# backend/tests/test_generate_lesson_live.py
# Run real workflows, including a repeated prompt, and capture stages and cache reuse.
# Latest captures: backend/tests/fixtures/smoke/

import json
import os
from datetime import UTC, datetime
from inspect import signature
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pytest

import lexical_learner.generate_lesson as workflow
from lexical_learner.database import connect_database
from lexical_learner.generate_cloze import generate_cloze


@pytest.mark.live
@pytest.mark.parametrize(
    "scenario,prompt",
    [
        ("driving_test", "我准备要去参加驾考，可是我不太熟悉车上常用的零件怎么说。"),
        ("driving_test_repeat", "我准备要去参加驾考，可是我不太熟悉车上常用的零件怎么说。"),
        (
            "seafood_pasta",
            "我在超市中买了海鲜混合装自己做奶油意大利面，这个烹饪和享用的过程有哪些值得学习的吗？",
        ),
    ],
)
def test_generate_lesson_live(monkeypatch, request, scenario, prompt):
    if request.config.option.markexpr != "live":
        pytest.skip('Explicitly select live tests with -m live -o addopts=""')

    destination = Path(__file__).parent / "fixtures/smoke" / scenario
    destination.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid4())
    existing = {}

    def load_existing(lesson):
        ids = [sense["sense_id"] for senses in lesson.values() for sense in senses]
        with connect_database() as connection:
            translations = {
                sense_id: {"language": "zh", "translation": text, "source": source}
                for sense_id, text, source in connection.execute(
                    "SELECT sense_id, translation, source FROM sense_translations "
                    "WHERE sense_id = ANY(%s) AND language = 'zh'",
                    (ids,),
                ).fetchall()
            }
            clozes = {}
            for sense_id, cloze_id, sentence, answer, source in connection.execute(
                "SELECT sense_id, id, sentence, answer, source FROM sense_clozes "
                "WHERE sense_id = ANY(%s) ORDER BY id",
                (ids,),
            ).fetchall():
                clozes.setdefault(sense_id, []).append(
                    {
                        "id": cloze_id,
                        "sentence": sentence,
                        "answer": answer,
                        "source": source,
                    }
                )
        return {"translations": translations, "clozes": clozes}

    def record(stage, inputs, operation):
        capture = {
            "run_id": run_id,
            "stage": stage,
            "captured_at": datetime.now(UTC).isoformat(),
            "model": os.environ["GOOGLE_MODEL"],
            "dictionary": "oewn:2025",
            "database": "PostgreSQL (real)",
            "input": inputs,
        }
        print(f"[{scenario}] {stage} started", flush=True)
        started = perf_counter()
        try:
            output = operation()
            capture["output"] = output
            return output
        except Exception as error:
            capture["error"] = {"type": type(error).__name__}
            raise
        finally:
            capture["elapsed_seconds"] = round(perf_counter() - started, 3)
            (destination / f"{stage}.json").write_text(
                json.dumps(capture, ensure_ascii=False, indent=2) + "\n"
            )
            print(f"[{scenario}] {stage}: {capture['elapsed_seconds']}s", flush=True)

    # Record real calls; every wrapped function still executes its original implementation.
    for name in ("generate_vocabulary", "lookup_words", "select_senses", "ensure_sense_content"):
        original = getattr(workflow, name)

        def traced(*args, _name=name, _original=original, **kwargs):
            inputs = dict(signature(_original).bind(*args, **kwargs).arguments)
            if _name == "ensure_sense_content":
                existing.update(
                    record("cache_before", inputs, lambda: load_existing(inputs["lesson"]))
                )
            return record(_name, inputs, lambda: _original(*args, **kwargs))

        monkeypatch.setattr(workflow, name, traced)

    result = record("generate_lesson", {"prompt": prompt}, lambda: workflow.generate_lesson(prompt))
    words = json.loads((destination / "generate_vocabulary.json").read_text())["output"]
    assert 1 <= len(words) <= 30
    assert all(isinstance(word, str) and word.strip() for word in words)
    senses = [sense for entries in result.values() for sense in entries]
    assert senses, "At least one WordNet sense must be selected"
    by_id = {sense["sense_id"]: sense for sense in senses}
    for sense_id, translation in existing["translations"].items():
        assert by_id[sense_id]["translation"] == translation
    for sense_id, clozes in existing["clozes"].items():
        assert by_id[sense_id]["clozes"] == clozes
    if scenario == "driving_test_repeat":
        assert existing["translations"], "Repeated prompt must reuse existing translations"
        assert existing["clozes"], "Repeated prompt must reuse existing clozes"
    print(
        f"[{scenario}] reused {len(existing['translations'])} translations "
        f"and {len(existing['clozes'])} senses with clozes",
        flush=True,
    )

    questions = {}
    with connect_database() as connection:
        for sense in senses:
            assert sense["translation"] is not None
            assert sense["translation"]["translation"].strip()
            assert sense["clozes"]
            stored = connection.execute(
                "SELECT translation, source FROM sense_translations "
                "WHERE sense_id = %s AND language = %s",
                (sense["sense_id"], "zh"),
            ).fetchone()
            assert stored == (sense["translation"]["translation"], sense["translation"]["source"])
            for cloze in sense["clozes"]:
                questions[str(cloze["id"])] = cloze
                stored = connection.execute(
                    "SELECT sense_id, sentence, answer, source FROM sense_clozes WHERE id = %s",
                    (cloze["id"],),
                ).fetchone()
                assert stored == (
                    sense["sense_id"],
                    cloze["sentence"],
                    cloze["answer"],
                    cloze["source"],
                )
    questions = record(
        "generate_cloze",
        {"lesson": result},
        lambda: {
            cloze_id: generate_cloze(cloze["sentence"], cloze["answer"])
            for cloze_id, cloze in questions.items()
        },
    )
    print(
        json.dumps(
            {"scenario": scenario, "lesson": result, "questions": questions},
            ensure_ascii=False,
            indent=2,
        )
    )
