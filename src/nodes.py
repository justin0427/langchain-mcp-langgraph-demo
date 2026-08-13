"""LangGraph nodes for evidence collection and the three PR reviews."""

import re

from .config import make_model
from .github_agent import build_evidence_agent
from .progress import update_step
from .state import PullRequestState


def as_text(content: object) -> str:
    return content if isinstance(content, str) else str(content)


async def collect_evidence_node(state: PullRequestState) -> dict:
    update_step("evidence", "running", "LangChain 正透過 GitHub MCP 蒐集 diff、CI 與變更檔案")
    try:
        agent = await build_evidence_agent()
        request = (
            f"請蒐集 GitHub repository {state['repository']} 的 Pull Request "
            f"#{state['pull_number']} 的審查證據。"
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": request}]}
        )
        evidence = as_text(result["messages"][-1].content)
    except Exception as error:
        update_step("evidence", "failed", f"蒐證失敗：{error}")
        raise
    update_step("evidence", "done", "已取得可核對的 PR 證據")
    return {"evidence": evidence}


async def review_with_focus(
    evidence: str, focus: str, instructions: str, progress_key: str
) -> str:
    update_step(progress_key, "running", f"正在分析{focus}")
    try:
        response = await make_model().ainvoke(
            "你是 PR 審查助手。只能根據下列蒐集到的證據，不可臆測看不到的程式碼。"
            f"\n\n審查焦點：{focus}\n要求：{instructions}"
            f"\n\nPR 證據：\n{evidence}"
        )
        result = as_text(response.content)
    except Exception as error:
        update_step(progress_key, "failed", f"審查失敗：{error}")
        raise
    update_step(progress_key, "done", "審查結果已寫入 State")
    return result


async def quality_review_node(state: PullRequestState) -> dict:
    result = await review_with_focus(
        state["evidence"],
        "程式品質與可維護性",
        "找出複雜度、命名、重複、錯誤處理與可讀性風險；每點都標示證據或說明證據不足。",
        "quality",
    )
    return {"findings": [f"## 程式品質\n{result}"]}


async def security_review_node(state: PullRequestState) -> dict:
    result = await review_with_focus(
        state["evidence"],
        "資安風險",
        "檢查機密資訊、輸入驗證、授權、注入、危險檔案操作與依賴風險。無法從證據判定時要明確說明。",
        "security",
    )
    return {"findings": [f"## 資安風險\n{result}"]}


async def test_impact_review_node(state: PullRequestState) -> dict:
    result = await review_with_focus(
        state["evidence"],
        "測試與發布影響",
        "根據變更檔案、CI 與 diff，說明需要補強的測試、回歸風險與發布前檢查。",
        "tests",
    )
    return {"findings": [f"## 測試與發布影響\n{result}"]}


async def write_recommendation_node(state: PullRequestState) -> dict:
    update_step("summary", "running", "正在彙整三個平行審查結果")
    findings = "\n\n".join(state["findings"])
    try:
        response = await make_model().ainvoke(
            "你是合併前檢查的總結者。只根據 PR 證據與三份檢查結果寫繁體中文摘要。"
            "第一行必須精確輸出 RISK: HIGH 或 RISK: LOW。若 CI 失敗、發現可能的機密／"
            "注入／授權問題，或證據不足以安全判定，輸出 HIGH。之後以『結論』『待處理事項』"
            "與『合併建議』三個標題寫報告。\n\n"
            f"PR 證據：\n{state['evidence']}\n\n檢查結果：\n{findings}"
        )
        recommendation = as_text(response.content)
    except Exception as error:
        update_step("summary", "failed", f"彙整失敗：{error}")
        raise
    risk_level = "HIGH" if re.search(r"^RISK:\s*HIGH", recommendation, re.MULTILINE) else "LOW"
    update_step("summary", "done", f"已判定風險：{risk_level}")
    return {"recommendation": recommendation, "risk_level": risk_level}
