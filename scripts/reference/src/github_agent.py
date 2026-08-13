"""透過外部 GitHub MCP 蒐集 PR 證據，並先驗證 PR 存取權。"""

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from .config import get_settings, make_model, require_github_token


async def get_github_mcp_tools():
    """連到唯讀 GitHub MCP，取得它公開的工具清單。"""
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
    tools = await client.get_tools()
    if not tools:
        raise RuntimeError("GitHub MCP returned no tools. Check the token, URL, and network.")
    return tools


def mcp_response_text(response: object) -> str:
    """把 MCP 回應整理成字串，供程式判斷，不交給 LLM 解讀。"""
    if isinstance(response, list):
        return "\n".join(
            str(item.get("text", item)) if isinstance(item, dict) else str(item)
            for item in response
        )
    return str(response)


async def verify_pull_request_access(repository: str, pull_number: int) -> None:
    """直接呼叫 MCP 讀取 PR；讀不到就停止，不浪費 LLM 呼叫。"""
    owner, repo = repository.split("/", maxsplit=1)
    tools = await get_github_mcp_tools()
    pr_reader = next((tool for tool in tools if tool.name == "pull_request_read"), None)
    if pr_reader is None:
        raise RuntimeError("GitHub MCP 沒有提供 pull_request_read；請檢查 MCP toolset 設定。")

    try:
        response = await pr_reader.ainvoke(
            {"method": "get", "owner": owner, "repo": repo, "pullNumber": pull_number}
        )
    except Exception as error:
        raise RuntimeError(
            f"GitHub MCP 無法讀取 {repository} 的 PR #{pull_number}：{error}"
        ) from error

    details = mcp_response_text(response).lower()
    failure_markers = ("failed", "not found", "404", "401", "403", "forbidden")
    if any(marker in details for marker in failure_markers):
        raise RuntimeError(
            f"GitHub MCP 讀不到 {repository} 的 PR #{pull_number}。"
            "請確認 --repo 是 PR Lab 的 OWNER/REPO、--pr 是正確編號，"
            "並確認 fine-grained PAT 已選取該 repository 且獲准存取。"
        )

    print(f"✅ GitHub MCP 已確認可讀取 {repository} 的 PR #{pull_number}")


async def build_evidence_agent():
    """建立只讀 Agent；它只能使用 GitHub MCP 提供的工具。"""
    tools = await get_github_mcp_tools()
    print("Discovered read-only GitHub MCP tools:", ", ".join(tool.name for tool in tools))
    # system_prompt 限制 Agent：只蒐證、不猜測、也不做任何寫入操作。
    return create_agent(
        model=make_model(),
        tools=tools,
        system_prompt=(
            "You are a Pull Request evidence collector. The requested PR was already "
            "verified as readable through GitHub MCP. Use only the supplied GitHub MCP tools. "
            "Obtain its details, changed files, diff, commits, and CI/status when available. "
            "If the PR body references an Issue, read that issue. Return factual evidence in "
            "Traditional Chinese with these headings: PR 概要, 變更範圍, CI 狀態, 可核對的風險線索. "
            "Include file paths and facts; do not invent code that you did not retrieve. "
            "Do not make any write request."
        ),
    )
