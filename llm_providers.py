"""
LLM providers with automatic fallback.

Providers are tried in the order given by LLM_ORDER in .env (default: DEFAULT_ORDER).
If a provider errors, times out, hits a rate limit or returns an empty response,
the next provider in the list is used.
"""
import logging
import os
from typing import Any, Callable, Dict, List, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import BaseModel


# google-genai logs an "automatic function calling" warning on every request
logging.getLogger("google_genai.models").setLevel(logging.ERROR)


DEFAULT_ORDER = "gemini,groq"
REQUEST_TIMEOUT = 60  # seconds before giving up on a provider


def _gemini() -> BaseChatModel:
    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
        timeout=REQUEST_TIMEOUT,
        max_retries=2,  # Gemini often returns short-lived 503 "high demand" errors
    )


def _groq() -> BaseChatModel:
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        timeout=REQUEST_TIMEOUT,
        max_retries=1,
    )


# provider name -> (env var holding its API key, factory)
PROVIDERS: Dict[str, Tuple[str, Callable[[], BaseChatModel]]] = {
    "gemini": ("GEMINI_API_KEY", _gemini),
    "groq": ("GROQ_API_KEY", _groq),
}


def load_models() -> List[Tuple[str, BaseChatModel]]:
    """
    Builds the chat models in fallback order, skipping any provider without an API key.
    """
    order = [p.strip().lower() for p in os.getenv("LLM_ORDER", DEFAULT_ORDER).split(",") if p.strip()]

    models = []
    for name in order:
        if name not in PROVIDERS:
            print(f"[LLM] Unknown provider '{name}' in LLM_ORDER, skipping.")
            continue
        key_var, factory = PROVIDERS[name]
        if not os.getenv(key_var):
            print(f"[LLM] Skipping {name}: {key_var} is not set.")
            continue
        models.append((name, factory()))

    if not models:
        raise RuntimeError("No LLM provider available. Set GEMINI_API_KEY and/or GROQ_API_KEY in .env")

    print(f"[LLM] Provider order: {' -> '.join(name for name, _ in models)}")
    return models


def with_schema(model: BaseChatModel, schema: type[BaseModel]) -> Runnable:
    """
    Structured output that works on every provider. Groq needs strict mode,
    otherwise gpt-oss sometimes echoes the JSON schema back instead of filling it.
    """
    if isinstance(model, ChatGroq):
        return model.with_structured_output(schema, method="json_schema", strict=True)
    return model.with_structured_output(schema, method="json_schema")


def invoke_with_fallback(
    models: List[Tuple[str, BaseChatModel]],
    build_chain: Callable[[BaseChatModel], Runnable],
    inputs: Dict[str, Any],
) -> Any:
    """
    Runs the chain built by build_chain(model) on each provider in turn and
    returns the first non-empty result.
    """
    errors = []
    for name, model in models:
        try:
            result = build_chain(model).invoke(inputs)
            if result is None or (isinstance(result, AIMessage) and not result.text.strip()):
                raise ValueError("empty response")
            print(f"[LLM] Response from {name}")
            return result
        except Exception as e:
            print(f"[LLM] {name} failed: {type(e).__name__}: {str(e)[:200]}")
            errors.append(f"{name}: {e}")

    raise RuntimeError("All LLM providers failed:\n" + "\n".join(errors))
