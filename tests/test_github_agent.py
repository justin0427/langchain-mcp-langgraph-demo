"""不連網的測試：確認讀不到 PR 時不會繼續交給 LLM。"""

import unittest
from unittest.mock import patch

from src.github_agent import verify_pull_request_access


class FakePullRequestReader:
    """模擬 GitHub MCP 的 pull_request_read 工具。"""

    name = "pull_request_read"

    def __init__(self, response: object) -> None:
        self.response = response
        self.arguments: dict | None = None

    async def ainvoke(self, arguments: dict) -> object:
        self.arguments = arguments
        return self.response


class VerifyPullRequestAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_stops_when_mcp_returns_not_found(self) -> None:
        reader = FakePullRequestReader(
            [{"type": "text", "text": "failed to get pull request: 404 Not Found"}]
        )
        with patch("src.github_agent.get_github_mcp_tools", return_value=[reader]):
            with self.assertRaisesRegex(RuntimeError, "讀不到 amy/pr-review-lab-amy 的 PR #1"):
                await verify_pull_request_access("amy/pr-review-lab-amy", 1)

        self.assertEqual(
            reader.arguments,
            {"method": "get", "owner": "amy", "repo": "pr-review-lab-amy", "pullNumber": 1},
        )

    async def test_allows_readable_pr_to_continue(self) -> None:
        reader = FakePullRequestReader([{"type": "text", "text": "PR details retrieved"}])
        with patch("src.github_agent.get_github_mcp_tools", return_value=[reader]):
            await verify_pull_request_access("amy/pr-review-lab-amy", 1)


if __name__ == "__main__":
    unittest.main()
