"""彩色終端 PR 選單。"""

import json
import sys
from dataclasses import dataclass

import questionary
from questionary import Choice, Style

from .github_agent import get_github_mcp_tools, mcp_response_text


@dataclass(frozen=True)
class PullRequestSummary:
    number: int
    title: str
    author: str
    head: str
    base: str
    draft: bool
    url: str


async def list_open_pull_requests(repository: str) -> list[PullRequestSummary]:
    """直接透過 GitHub MCP 取得開啟中的 PR，不經過 LLM。"""
    owner, repo = repository.split("/", maxsplit=1)
    tools = await get_github_mcp_tools()
    pr_lister = next((tool for tool in tools if tool.name == "list_pull_requests"), None)
    if pr_lister is None:
        raise RuntimeError("GitHub MCP 沒有提供 list_pull_requests；請檢查 MCP toolset 設定。")
    try:
        response = await pr_lister.ainvoke(
            {
                "owner": owner,
                "repo": repo,
                "state": "open",
                "perPage": 100,
                "fields": ["number", "title", "state", "draft", "user", "head", "base", "updated_at", "html_url"],
            }
        )
    except Exception as error:
        raise RuntimeError(f"GitHub MCP 無法列出 {repository} 的 PR：{error}") from error
    try:
        payload = json.loads(mcp_response_text(response))
    except json.JSONDecodeError as error:
        raise RuntimeError("GitHub MCP 回傳的 PR 清單格式無法解析，請稍後再試。") from error
    if isinstance(payload, dict):
        payload = payload.get("items", payload.get("pull_requests", []))
    if not isinstance(payload, list):
        raise RuntimeError("GitHub MCP 回傳的 PR 清單格式不正確。")
    summaries = []
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("number"), int):
            continue
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        head = item.get("head") if isinstance(item.get("head"), dict) else {}
        base = item.get("base") if isinstance(item.get("base"), dict) else {}
        summaries.append(PullRequestSummary(item["number"], str(item.get("title", "（沒有標題）")), str(user.get("login", "unknown")), str(head.get("ref", "unknown")), str(base.get("ref", "unknown")), bool(item.get("draft", False)), str(item.get("html_url", ""))))
    return summaries


SELECT_STYLE = Style(
    [
        ("qmark", "fg:#5f87ff bold"),
        ("question", "bold"),
        ("pointer", "fg:#ffaf00 bold"),
        ("highlighted", "fg:#ffaf00 bold"),
        ("selected", "fg:#00af87"),
        ("instruction", "fg:#808080"),
    ]
)


async def select_pull_request(
    repository: str, pull_requests: list[PullRequestSummary]
) -> int:
    """讓使用者以方向鍵選擇 PR，回傳選到的編號。"""
    if not pull_requests:
        raise RuntimeError(f"{repository} 目前沒有開啟中的 Pull Request。請先建立 PR 再執行。")
    if not sys.stdin.isatty():
        raise RuntimeError("目前不是互動式終端機；請加上 --pr <編號> 指定 Pull Request。")

    choices = []
    for pull_request in pull_requests:
        state = "🟡 Draft" if pull_request.draft else "🟢"
        short_title = pull_request.title if len(pull_request.title) <= 32 else f"{pull_request.title[:31]}…"
        short_head = pull_request.head if len(pull_request.head) <= 24 else f"{pull_request.head[:23]}…"
        title = (
            f"{state}  #{pull_request.number}  {short_title}  "
            f"· {pull_request.author}  · {short_head}"
        )
        choices.append(Choice(title=title, value=pull_request.number))

    questionary.print(f"Repository：{repository}", style="bold fg:#5f87ff")
    answer = questionary.select(
        f"找到 {len(pull_requests)} 個開啟中的 PR，請選擇：",
        choices=choices,
        instruction="（↑／↓ 移動，Enter 確認，Ctrl+C 取消）",
        qmark="◆",
        pointer="❯",
        style=SELECT_STYLE,
        use_shortcuts=False,
        use_indicator=False,
    ).ask_async()
    answer = await answer
    if answer is None:
        raise RuntimeError("已取消 PR 選擇。")
    return int(answer)
