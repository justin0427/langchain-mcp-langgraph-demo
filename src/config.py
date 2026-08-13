"""Runtime configuration and model construction."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()


@dataclass(frozen=True)
class Settings:
    github_token: str | None
    github_mcp_url: str
    ollama_base_url: str
    llm_model: str | None


def get_settings() -> Settings:
    return Settings(
        github_token=os.environ.get("GITHUB_TOKEN"),
        github_mcp_url=os.environ.get(
            "GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/readonly"
        ),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        llm_model=os.environ.get("LLM_MODEL"),
    )


def make_model() -> ChatOllama:
    settings = get_settings()
    if not settings.llm_model or settings.llm_model == "your-tool-calling-model":
        raise RuntimeError(
            "Set LLM_MODEL in .env to an installed Ollama model with tool-calling support."
        )
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )


def require_github_token() -> str:
    token = get_settings().github_token
    if not token or token == "github_pat_replace_me":
        raise RuntimeError("Set GITHUB_TOKEN in .env to a read-only GitHub fine-grained PAT.")
    return token
