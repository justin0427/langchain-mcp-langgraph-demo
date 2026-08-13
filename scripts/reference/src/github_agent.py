"""透過外部 GitHub MCP Server 蒐集 PR 證據的 LangChain Agent。"""

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from .config import get_settings, make_model, require_github_token


async def build_evidence_agent():
    """建立只讀 Agent；它只能使用 GitHub MCP 提供的工具。"""
    settings = get_settings()
    token = require_github_token()
    # 不自己寫 MCP Server，而是連線到 GitHub 官方提供的遠端唯讀 endpoint。
    client = MultiServerMCPClient(
        {
            "github": {
                "transport": "http",
                "url": settings.github_mcp_url,
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "X-MCP-Toolsets": "repos,issues,pull_requests,actions",
                    "X-MCP-Readonly": "true",
                },
            }
        }
    )
    # 將 MCP Server 公開的工具轉成 LangChain Agent 可呼叫的 tools。
    tools = await client.get_tools()
    if not tools:
        raise RuntimeError("GitHub MCP returned no tools. Check the token, URL, and network.")

    print("Discovered read-only GitHub MCP tools:", ", ".join(tool.name for tool in tools))
    # system_prompt 限制 Agent：只蒐證、不猜測、也不做任何寫入操作。
    return create_agent(
        model=make_model(),
        tools=tools,
        system_prompt=(
            "You are a Pull Request evidence collector. Use only the supplied GitHub MCP "
            "tools. For the requested PR, obtain its details, changed files, diff, commits, "
            "and CI/status when available. If the PR body references an Issue, read that issue. "
            "Return factual evidence in Traditional Chinese with these headings: PR 概要, "
            "變更範圍, CI 狀態, 可核對的風險線索. Include file paths and facts; do not "
            "invent code that you did not retrieve. Do not make any write request."
        ),
    )
