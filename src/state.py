"""Shared LangGraph state schema."""

import operator
from typing import Annotated, Literal

from typing_extensions import TypedDict


class PullRequestState(TypedDict):
    repository: str
    pull_number: int
    evidence: str
    findings: Annotated[list[str], operator.add]
    risk_level: Literal["LOW", "HIGH"]
    recommendation: str
    outcome: str
