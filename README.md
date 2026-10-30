# Lexical Learner

Generate up to 30 English words and phrases from a scenario using LangChain and Google Gemini.

## Setup

```bash
cd backend
uv sync --locked
export GOOGLE_API_KEY="your-api-key"
export GOOGLE_MODEL="gemini-3.1-flash-lite"
```

`generate_vocabulary(prompt)` returns a list of strings. Inputs exceeding 1024 UTF-8 bytes return an empty list without contacting Gemini. Invalid JSON raises its native parsing error; an invalid result structure raises `ValueError`. Results are limited to 30 items.

## Live smoke test

Normal `uv run pytest` excludes live tests and makes no API calls. There are currently no non-live tests, so pytest reports one deselected test.

To explicitly call Gemini and print the result:

```bash
uv run pytest -m live -o addopts="" -s
```

This uses the Chinese driving-test scenario and checks for 1–30 non-empty strings. Review vocabulary relevance manually; exact terms and counts are not fixed.

A real function input/output example is saved in `backend/tests/fixtures/generate_vocabulary_live.json` for future mocked tests. It contains no credentials.

## Local WordNet resources

Install the pinned dictionary once, after `uv sync --locked`:

```bash
cd backend
uv run python -m wn download oewn:2025
```

Wn stores the downloaded data and its internal index in `~/.wn_data` by default, outside this repository. Subsequent dictionary queries are offline; keep the complete dataset out of Git.

A real batch lookup example is saved in `backend/tests/fixtures/lookup_words.json`. Each input expression maps to all matching senses; unmatched expressions map to an empty list. Each sense includes its ID, definitions, and combined sense/synset examples.

Dictionary data: [Open English WordNet 2025](https://en-word.net/), by the Open English WordNet contributors, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The example reproduces dictionary text without rewriting it.
