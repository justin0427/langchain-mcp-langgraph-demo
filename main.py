"""從終端機啟動唯讀 PR 審查工作流，顯示進度並產生 Markdown 報告。"""

import argparse
import asyncio
from contextlib import suppress
from pathlib import Path

from rich.markdown import Markdown
from rich.panel import Panel

from src.github_agent import verify_pull_request_access
from src.progress import ReviewDashboard, set_dashboard
from src.report import build_markdown_report, save_markdown_report
from src.workflow import build_workflow

PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only GitHub PR merge-readiness checker")
    parser.add_argument("--repo", required=True, help="GitHub repository in OWNER/REPO format")
    parser.add_argument("--pr", required=True, type=int, help="Pull Request number")
    args = parser.parse_args()
    if args.repo.count("/") != 1:
        parser.error("--repo must use OWNER/REPO format")
    return args


async def main() -> None:
    args = parse_args()
    dashboard = ReviewDashboard()
    result: dict | None = None
    failure: str | None = None

    with dashboard:
        set_dashboard(dashboard)
        animation_task = asyncio.create_task(animate_dashboard(dashboard))
        try:
            dashboard.update("mcp_access", "running", "直接用 GitHub MCP 讀取指定 PR")
            await verify_pull_request_access(args.repo, args.pr)
            dashboard.update("mcp_access", "done", "PR 存取權已確認，不會讓 LLM 猜測")

            result = await build_workflow().ainvoke(
                {
                    "repository": args.repo,
                    "pull_number": args.pr,
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
