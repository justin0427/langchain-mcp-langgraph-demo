"""LangChain Agent that gathers evidence through GitHub's external MCP Server."""

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from .config import get_settings, make_model, require_github_token


async def build_evidence_agent():
    """Return a read-only Agent for collecting verifiable Pull Request evidence."""
    settings = get_settings()
    token = require_github_token()
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
    tools = await client.get_tools()
    if not tools:
        raise RuntimeError("GitHub MCP returned no tools. Check the token, URL, and network.")

    print("Discovered read-only GitHub MCP tools:", ", ".join(tool.name for tool in tools))
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
