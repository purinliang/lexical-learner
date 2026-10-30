# backend/src/lexical_learner/llm.py
# Create the Gemini client from environment variables with retries disabled.

import os

from langchain_google_genai import ChatGoogleGenerativeAI


def create_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=os.environ["GOOGLE_MODEL"],
        api_key=os.environ["GOOGLE_API_KEY"],
        vertexai=False,
        max_retries=0,
    )
