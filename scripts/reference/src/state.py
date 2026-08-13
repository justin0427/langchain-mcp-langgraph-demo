"""定義 LangGraph 在各個 Node 之間傳遞的共同工作單（State）。"""

import operator
from typing import Annotated, Literal

from typing_extensions import TypedDict


class PullRequestState(TypedDict):
    # 這兩項由 main.py 的命令列參數提供。
    repository: str
    pull_number: int
    # LangChain Agent 從 GitHub MCP 蒐集到的可核對資料。
    evidence: str
    # 三個平行 Node 都會新增 findings；operator.add 會把清單合併而非覆蓋。
    findings: Annotated[list[str], operator.add]
    # 彙整 Node 判斷出的風險，供後面的條件 Edge 分流。
    risk_level: Literal["LOW", "HIGH"]
    recommendation: str
    outcome: str
