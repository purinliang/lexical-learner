# backend/src/lexical_learner/generate_cloze.py
# Replace the first complete answer with underscores without changing other words.

import re


def generate_cloze(sentence: str, answer: str) -> str:
    if not answer.strip():
        raise ValueError("The answer must not be blank")
    question, count = re.subn(
        rf"(?<!\w){re.escape(answer)}(?!\w)",
        "_" * (len(answer) + 2),
        sentence,
        count=1,
        flags=re.IGNORECASE,
    )
    if not count:
        raise ValueError("The sentence must contain the complete answer")
    return question
