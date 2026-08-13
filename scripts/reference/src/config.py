"""讀取 .env，並建立要交給 LangChain 使用的 Ollama 模型。"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

# 程式啟動時讀取專案根目錄的 .env；Token 不會寫進程式碼。
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """集中保存程式需要的環境設定，避免各檔案重複讀取環境變數。"""
    github_token: str | None
    github_mcp_url: str
    ollama_base_url: str
    llm_model: str | None


def get_settings() -> Settings:
    """從 .env 取得設定；沒有填的值會保留為 None。"""
    return Settings(
        github_token=os.environ.get("GITHUB_TOKEN"),
        github_mcp_url=os.environ.get(
            "GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/readonly"
        ),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        llm_model=os.environ.get("LLM_MODEL"),
    )


def make_model() -> ChatOllama:
    """建立 LangChain 可呼叫的本機 Ollama 聊天模型。"""
    settings = get_settings()
    if not settings.llm_model or settings.llm_model == "your-tool-calling-model":
        raise RuntimeError(
            "請在 .env 設定支援 tool calling 的 LLM_MODEL。"
        )
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )


def require_github_token() -> str:
    """確認學生已填入 GitHub 唯讀 PAT，否則在連線前先停止。"""
    token = get_settings().github_token
    if not token or token == "github_pat_replace_me":
        raise RuntimeError("請在 .env 設定唯讀 GitHub fine-grained PAT。")
    return token
