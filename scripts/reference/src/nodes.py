"""LangGraph 的蒐證、平行審查與報告 Node。"""

import re

from .config import make_model
from .github_agent import build_evidence_agent
from .state import PullRequestState


def as_text(content: object) -> str:
    """將不同模型可能回傳的內容格式統一轉成字串。"""
    return content if isinstance(content, str) else str(content)


async def collect_evidence_node(state: PullRequestState) -> dict:
    # 將 State 的 PR 資訊交給 LangChain Agent，並只回寫 evidence 欄位。
    agent = await build_evidence_agent()
    request = (
        f"請蒐集 GitHub repository {state['repository']} 的 Pull Request "
        f"#{state['pull_number']} 的審查證據。"
    )
    result = await agent.ainvoke({"messages": [{"role": "user", "content": request}]})
    return {"evidence": as_text(result["messages"][-1].content)}


async def review_with_focus(evidence: str, focus: str, instructions: str) -> str:
    # 三種審查共用同一份證據，只替換各自的檢查焦點與規則。
    response = await make_model().ainvoke(
        "你是 PR 審查助手。只能根據下列蒐集到的證據，不可臆測看不到的程式碼。"
        f"\n\n審查焦點：{focus}\n要求：{instructions}"
        f"\n\nPR 證據：\n{evidence}"
    )
    return as_text(response.content)


async def quality_review_node(state: PullRequestState) -> dict:
    # 回傳 list，讓 State 的 operator.add 可以與其他平行結果合併。
    result = await review_with_focus(
        state["evidence"],
        "程式品質與可維護性",
        "找出複雜度、命名、重複、錯誤處理與可讀性風險；每點都標示證據或說明證據不足。",
    )
    return {"findings": [f"## 程式品質\n{result}"]}


async def security_review_node(state: PullRequestState) -> dict:
    result = await review_with_focus(
        state["evidence"],
        "資安風險",
        "檢查機密資訊、輸入驗證、授權、注入、危險檔案操作與依賴風險。無法從證據判定時要明確說明。",
    )
    return {"findings": [f"## 資安風險\n{result}"]}


async def test_impact_review_node(state: PullRequestState) -> dict:
    result = await review_with_focus(
        state["evidence"],
        "測試與發布影響",
        "根據變更檔案、CI 與 diff，說明需要補強的測試、回歸風險與發布前檢查。",
    )
    return {"findings": [f"## 測試與發布影響\n{result}"]}


async def write_recommendation_node(state: PullRequestState) -> dict:
    # defer=True 會讓此 Node 等三個平行審查結果都回來後才執行。
    findings = "\n\n".join(state["findings"])
    response = await make_model().ainvoke(
        "你是合併前檢查的總結者。只根據 PR 證據與三份檢查結果寫繁體中文摘要。"
        "第一行必須精確輸出 RISK: HIGH 或 RISK: LOW。若 CI 失敗、發現可能的機密／"
        "注入／授權問題，或證據不足以安全判定，輸出 HIGH。之後以『結論』『待處理事項』"
        "與『合併建議』三個標題寫報告。\n\n"
        f"PR 證據：\n{state['evidence']}\n\n檢查結果：\n{findings}"
    )
    recommendation = as_text(response.content)
    # 讀取固定格式的第一行，供 workflow.py 的條件 Edge 做分流。
    risk_level = "HIGH" if re.search(r"^RISK:\s*HIGH", recommendation, re.MULTILINE) else "LOW"
    return {"recommendation": recommendation, "risk_level": risk_level}
