"""
Provider-agnostic LLM factory.

Switch LLM provider by changing env vars — no code changes needed:
  LLM_PROVIDER=gemini | openai | groq
  LLM_MODEL=gemini-2.0-flash | gpt-4o-mini | llama-3.1-70b-versatile
  LLM_API_KEY=your-key
"""

from langchain_core.language_models import BaseChatModel

from app.config import get_settings


def create_llm() -> BaseChatModel:
    """Create an LLM instance based on env configuration.
    
    Returns:
        BaseChatModel: A LangChain-compatible chat model.
    
    Raises:
        ValueError: If provider is not supported.
    """
    settings = get_settings()

    match settings.LLM_PROVIDER:
        case "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL,
                google_api_key=settings.LLM_API_KEY,
                temperature=settings.LLM_TEMPERATURE,
                include_thoughts=True,
            )

        case "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                temperature=settings.LLM_TEMPERATURE,
            )

        case "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                temperature=settings.LLM_TEMPERATURE,
            )

        case _:
            raise ValueError(
                f"Unknown LLM provider: '{settings.LLM_PROVIDER}'. "
                f"Supported: gemini, openai, groq"
            )


def create_embeddings():
    """Create an embedding model based on env configuration.
    
    Returns:
        Embeddings instance for vector generation.
    """
    settings = get_settings()

    match settings.EMBEDDING_PROVIDER:
        case "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            return GoogleGenerativeAIEmbeddings(
                model=f"models/{settings.EMBEDDING_MODEL}",
                google_api_key=settings.LLM_API_KEY,
            )

        case "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.LLM_API_KEY,
            )

        case _:
            raise ValueError(
                f"Unknown embedding provider: '{settings.EMBEDDING_PROVIDER}'. "
                f"Supported: gemini, openai"
            )
