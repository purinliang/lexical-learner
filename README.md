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
