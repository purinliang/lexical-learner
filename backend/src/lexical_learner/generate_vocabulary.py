# backend/src/lexical_learner/generate_vocabulary.py
# Generate up to 30 English words or phrases for a user-provided scenario.
# I/O fixture: backend/tests/fixtures/generate_vocabulary_live.json

import json

from langchain_core.messages import HumanMessage, SystemMessage

from lexical_learner.llm import create_model


def generate_vocabulary(prompt: str) -> list[str]:
    if len(prompt.encode("utf-8")) > 1024:
        return []

    model = create_model()

    response = model.invoke(
        [
            SystemMessage(
                content=(
                    "Generate useful English words and phrases relevant to "
                    "the user's scenario. Prioritize practical vocabulary, "
                    "without forcing a minimum number of items. "
                    "Prefer dictionary headwords: base verbs, singular nouns and adjectives. "
                    "Keep established terms such as black pepper or air fryer, but avoid loose "
                    "descriptive combinations such as fresh parsley; use parsley instead. "
                    "Include practical associated ingredients, seasonings, actions, tools, "
                    "textures and colours when relevant, including reasonably implied concepts. "
                    "Return only a JSON array of at most 30 strings."
                )
            ),
            HumanMessage(content=prompt),
        ],
        response_mime_type="application/json",
        response_schema={
            "type": "array",
            "items": {"type": "string"},
        },
    )

    words = json.loads(response.text)
    if not isinstance(words, list) or any(
        not isinstance(word, str) or not word.strip() for word in words
    ):
        raise ValueError("Expected a JSON array of non-empty strings")
    return words[:30]
