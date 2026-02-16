"""Compatibilità import LangChain/OpenAI tra versioni legacy e recenti."""

from importlib.util import find_spec

HAS_LANGCHAIN_OPENAI = find_spec("langchain_openai") is not None

if HAS_LANGCHAIN_OPENAI:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
else:
    try:
        # Fallback legacy (langchain 0.0.x / 0.1.x)
        from langchain.chat_models import ChatOpenAI
        from langchain.embeddings import OpenAIEmbeddings
    except ImportError:
        # Fallback community per alcune installazioni più recenti
        from langchain_community.chat_models import ChatOpenAI
        from langchain_community.embeddings import OpenAIEmbeddings


def create_chat_openai(*, model: str, temperature: float, api_key: str) -> ChatOpenAI:
    """Istanzia ChatOpenAI supportando sia API nuove che legacy."""
    if HAS_LANGCHAIN_OPENAI:
        return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)

    # API legacy
    return ChatOpenAI(model_name=model, temperature=temperature, openai_api_key=api_key)


def create_openai_embeddings(*, api_key: str) -> OpenAIEmbeddings:
    """Istanzia OpenAIEmbeddings supportando API nuove e legacy."""
    if HAS_LANGCHAIN_OPENAI:
        return OpenAIEmbeddings(api_key=api_key)

    return OpenAIEmbeddings(openai_api_key=api_key)
