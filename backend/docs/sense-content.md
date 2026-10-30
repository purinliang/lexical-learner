# Sense content

`generate_lesson(prompt)` generates vocabulary, looks up WordNet senses and asks
Gemini to select definitions. It then calls
`ensure_sense_content(lesson, language="zh", source="gemini")` on selected senses.
The selection call receives only the scenario and definitions, as before.

Content loading uses two batch queries, one for translations in the requested
language and one for clozes. If every selected sense has both, there is no
content-generation call. Otherwise one Gemini request contains only incomplete
senses and their missing fields, grounded in the word and WordNet definitions.
Short local references map responses back to sense IDs. No dictionary examples
or synonyms are sent to this call.

Valid new content is inserted with explicit language and source values. Existing
content is never updated. All references and requested fields must be returned,
with no extras. The entire batch is validated before opening the write
connection. Each cloze is checked with `generate_cloze(sentence, answer)`;
invalid content rejects the batch without saving any generated fields. Invalid
JSON, provider errors and database errors propagate. Failed writes roll back.
The read connection closes before Gemini is invoked. Saving uses a separate
connection and a short write transaction; no database connection is kept open
while waiting for Gemini.
There are no retries or concurrency controls.

Each returned sense retains its original WordNet fields and adds:

- `translation`: `{language, translation, source}`, or `null` when unavailable.
- `clozes`: saved `{id, sentence, answer, source}`
  records, or an empty list. These are separate from WordNet's `examples`.

Gemini generates English cloze sentences. The answer is the actual word form in
the sentence (for example, `running` rather than `run`). It must be nonblank and
appear as a complete word or phrase; otherwise the entire batch is rejected.
Question rendering is independent: `generate_cloze(sentence, answer)` replaces
only the first complete match, ignoring case, with `len(answer) + 2` underscores. It does not
replace `car` inside `carpet`, and does not access Gemini or PostgreSQL.
Persistence uses the renderer to validate clozes but does not store questions.
Semantic quality still depends on Gemini. No sentence translations are generated.

`sense_reviews` is reserved for actual review events and is not written during
lesson generation.

## Local setup and tests

Start PostgreSQL using [local-database.md](local-database.md). Apply the migration
once before generating lessons (run from `backend/`):

```bash
docker compose -f compose.local.yaml exec -T postgres \
  psql -U lexical-learner -d lexical-learner -v ON_ERROR_STOP=1 --single-transaction \
  < migrations/0001_create_sense_tables.sql
```

Run mocked content and workflow tests without Gemini or PostgreSQL:

```bash
uv run pytest tests/test_ensure_sense_content.py tests/test_generate_lesson.py tests/test_generate_cloze.py
```

Run local PostgreSQL tests with mocked Gemini:

```bash
uv run --env-file .env pytest tests/test_sense_content_database.py tests/test_sense_reviews.py
```

The database tests use temporary tables and roll back, preserving application
tables and their contents. They skip when `DATABASE_URL` is absent. The fixture
`sense_content_synthetic.json` is synthetic, not a captured provider response.
Normal pytest still excludes live Gemini tests by default.

To explicitly test only content generation against Gemini, reusing one selected
clutch sense from `generate_lesson_live.json` with database I/O mocked:

```bash
uv run --env-file .env pytest tests/test_ensure_sense_content_live.py -m live -o addopts="" -s
```

This makes one real Gemini call, prints the content and cloze question, and saves
the first successful result to `tests/fixtures/ensure_sense_content_live.json`.
The capture marks database I/O as mocked, including its synthetic row ID. It does
not write to application tables or overwrite an existing capture.

Both live tests print `elapsed_seconds`, measured around the function under test
using `time.perf_counter()`. This excludes fixture setup and assertions; it is
function duration, not a provider-reported inference time. New content captures
include this measurement. Existing captures are preserved without backfilling
estimated timings.
