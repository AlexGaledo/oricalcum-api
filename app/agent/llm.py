"""Gemini chat model configuration (LCEL Runnable).

Uses langchain-google-genai's ChatGoogleGenerativeAI. The model id and API key
come from settings; token streaming is handled by the caller via `.astream`.
"""

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings


def build_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured — the AI assistant is unavailable."
        )
    return ChatGoogleGenerativeAI(
        model=settings.agent_model,
        google_api_key=settings.google_api_key,
        temperature=0.3,
    )
