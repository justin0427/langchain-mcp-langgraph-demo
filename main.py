"""從終端機啟動唯讀 PR 審查工作流，顯示進度並產生 Markdown 報告。"""

import argparse
import asyncio
from contextlib import suppress
from pathlib import Path

from rich.markdown import Markdown
from rich.panel import Panel
from rich.console import Console

from src.github_agent import verify_pull_request_access
from src.pr_selector import list_open_pull_requests, select_pull_request
from src.progress import ReviewDashboard, set_dashboard
from src.report import build_markdown_report, save_markdown_report
from src.workflow import build_workflow

PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only GitHub PR merge-readiness checker")
    parser.add_argument("--repo", required=True, help="GitHub repository in OWNER/REPO format")
    parser.add_argument(
        "--pr",
        type=int,
        help="Pull Request number；省略時會顯示彩色方向鍵選單",
    )
    args = parser.parse_args()
    if args.repo.count("/") != 1:
        parser.error("--repo must use OWNER/REPO format")
    return args


async def main() -> None:
    args = parse_args()
    pull_number = args.pr
    if pull_number is None:
        console = Console()
        try:
            with console.status("[bold cyan]正在透過 GitHub MCP 讀取開啟中的 PR…"):
                pull_requests = await list_open_pull_requests(args.repo)
            pull_number = await select_pull_request(args.repo, pull_requests)
        except RuntimeError as error:
            console.print(f"[bold red]❌ 無法選擇 PR：{error}[/bold red]")
            raise SystemExit(2) from error

    dashboard = ReviewDashboard()
    result: dict | None = None
    failure: str | None = None

    if not dashboard.can_animate:
        dashboard.console.print(
            "[bold yellow]⚠️ 目前不是互動式終端機，無法播放即時動畫；"
            "請改在 Windows Terminal、PowerShell 或 VS Code 的『終端機』執行，"
            "不要使用 Output／Code Runner 面板。[/bold yellow]"
        )

    with dashboard:
        set_dashboard(dashboard)
        animation_task = asyncio.create_task(animate_dashboard(dashboard))
        try:
            dashboard.update("mcp_access", "running", f"直接用 GitHub MCP 驗證 PR #{pull_number}")
            await verify_pull_request_access(args.repo, pull_number)
            dashboard.update("mcp_access", "done", f"PR #{pull_number} 存取權已確認，不會讓 LLM 猜測")

            result = await build_workflow().ainvoke(
                {
                    "repository": args.repo,
                    "pull_number": pull_number,
                    "evidence": "",
                    "findings": [],
                    "risk_level": "LOW",
                    "recommendation": "",
                    "outcome": "",
                }
            )
        except RuntimeError as error:
            dashboard.update("mcp_access", "failed", "repo、PR 編號或 PAT 無法讀取")
            failure = str(error)
        except Exception as error:
            failure = str(error)
        finally:
            animation_task.cancel()
            with suppress(asyncio.CancelledError):
                await animation_task
            set_dashboard(None)

    if failure:
        dashboard.console.print(f"[bold red]❌ 審查已停止：{failure}[/bold red]")
        dashboard.console.print("不會輸出空白審查報告；請修正上方失敗的元件後重試。")
        raise SystemExit(2)

    assert result is not None
    report_path = save_markdown_report(PROJECT_ROOT, result)
    report = build_markdown_report(result)
    dashboard.console.print(
        Panel.fit(
            f"報告已存到：{report_path.relative_to(PROJECT_ROOT)}",
            title="完成",
            border_style="green",
        )
    )
    dashboard.console.print(Markdown(report))


async def animate_dashboard(dashboard: ReviewDashboard) -> None:
    """每秒刷新多次，讓學生看得出程式仍在進行。"""
    while True:
        dashboard.tick()
        await asyncio.sleep(0.12)


if __name__ == "__main__":
    asyncio.run(main())
