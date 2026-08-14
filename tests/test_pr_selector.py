import asyncio
from unittest.mock import AsyncMock, Mock, patch

from src.pr_selector import PullRequestSummary, list_open_pull_requests, select_pull_request


class FakePullRequestLister:
    name = "list_pull_requests"

    def __init__(self) -> None:
        self.arguments = None

    async def ainvoke(self, arguments):
        self.arguments = arguments
        return [{"type": "text", "text": '[{"number":3,"title":"Add validation","draft":false,"html_url":"https://github.com/amy/lab/pull/3","user":{"login":"amy"},"head":{"ref":"feature"},"base":{"ref":"main"}}]'}]


def test_lists_open_pull_requests_from_github_mcp():
    lister = FakePullRequestLister()
    with patch("src.pr_selector.get_github_mcp_tools", return_value=[lister]):
        pull_requests = asyncio.run(list_open_pull_requests("amy/lab"))
    assert pull_requests[0].number == 3
    assert pull_requests[0].title == "Add validation"
    assert lister.arguments["state"] == "open"


def test_selects_pull_request_number_from_colored_terminal_menu():
    pull_requests = [
        PullRequestSummary(
            number=3,
            title="Add validation",
            author="amy",
            head="feature",
            base="main",
            draft=False,
            url="https://github.com/amy/lab/pull/3",
        )
    ]
    prompt = Mock()
    prompt.ask_async = AsyncMock(return_value=3)

    with patch("src.pr_selector.sys.stdin.isatty", return_value=True):
        with patch("src.pr_selector.questionary.select", return_value=prompt) as menu:
            selected = asyncio.run(select_pull_request("amy/lab", pull_requests))

    assert selected == 3
    assert menu.call_args.kwargs["choices"][0].value == 3
