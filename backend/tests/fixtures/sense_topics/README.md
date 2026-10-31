# Cooking scenario captures

These are real Gemini, local Open English WordNet 2025 and PostgreSQL taxonomy
observations, not approved golden expectations. The test reads existing taxonomy;
it does not create taxonomy nodes, translations or clozes.

Run explicitly from `backend/`:

```bash
uv run --env-file .env pytest tests/test_food_sense_topics_live.py -m live -o addopts="" -s
```

Each scenario records stage inputs, outputs, durations and a run ID. The initial
attempts under `initial_compositional_phrases/` had poor dictionary coverage.
The later attempts prefer canonical headwords. The pasta selection initially
failed with HTTP 400 using a larger schema; `select_senses_rejected_schema.json`
preserves that failure. Only selection was resumed using the captured vocabulary,
dictionary definitions and taxonomy after simplifying the schema.

The later pasta result selected 28 words / 35 senses; chicken selected 19 words /
24 senses. These counts describe the recorded runs, not guaranteed output sizes
or measures of semantic accuracy. Pasta rejected `garish`; `doneness` and chicken's
`air fryer` had no dictionary entry.

The captures predate the unmatched-phrase splitting fallback. They are preserved
unchanged: a new run can additionally look up component words, while retaining an
empty result for the unmatched full phrase. Component senses do not verify the
meaning of the full phrase.

`select_senses` now returns an array of `{index, topic_ids, subtopic_ids}` per
input term. Indices refer to its supplied definitions, and taxonomy IDs must exist
in its supplied tree. Multiple senses and multiple taxonomy links are allowed;
every chosen subtopic must include its parent topic. `generate_lesson` reattaches
WordNet content and human-readable taxonomy references locally. These links are
returned in the lesson only; no SQL association table is created.
