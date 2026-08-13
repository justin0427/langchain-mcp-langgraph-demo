"""從終端機啟動唯讀 PR 審查工作流。"""

import argparse
import asyncio

from src.github_agent import verify_pull_request_access
from src.workflow import build_workflow  # 匯入已組裝完成的 LangGraph 工作流


def parse_args() -> argparse.Namespace:
    """讀取學生在終端機輸入的 repository 與 PR 編號。"""
    parser = argparse.ArgumentParser(description="Read-only GitHub PR merge-readiness checker")
    parser.add_argument("--repo", required=True, help="GitHub repository in OWNER/REPO format")
    parser.add_argument("--pr", required=True, type=int, help="Pull Request number")
    args = parser.parse_args()
    if args.repo.count("/") != 1:
        parser.error("--repo must use OWNER/REPO format")
    return args


async def main() -> None:
    args = parse_args()
    try:
        # 直接用 MCP 讀一次指定 PR；失敗時不啟動任何 LLM 審查 Node。
        await verify_pull_request_access(args.repo, args.pr)
    except RuntimeError as error:
        print(f"❌ PR 存取檢查失敗：{error}")
        print("   已停止：不會啟動 LangChain Agent 或後續 LLM 審查。")
        raise SystemExit(2) from error

    # 建立第一張工作單（State），再交給 LangGraph 依 Edge 執行各個 Node。
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

    # 將流程最後留下的 State 分段印出，方便學生對照每個步驟的結果。
    print("\n--- LangChain 蒐集的 PR 證據 ---")
    print(result["evidence"])
    print("\n--- LangGraph 平行檢查 ---")
    print("\n\n".join(result["findings"]))
    print("\n--- 合併前建議 ---")
    print(result["recommendation"])
    print("\n--- 最終路由 ---")
    print(result["outcome"])


if __name__ == "__main__":
    asyncio.run(main())
