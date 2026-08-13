"""確認最終結果能被整理成可閱讀的 Markdown 報告。"""

import tempfile
import unittest
from pathlib import Path

from src.report import build_markdown_report, save_markdown_report


STATE = {
    "repository": "justin0427/pr-review-lab-justin",
    "pull_number": 1,
    "evidence": "PR 有 2 個變更檔案。",
    "findings": ["## 程式品質\n正常", "## 資安風險\n無明顯問題"],
    "risk_level": "LOW",
    "recommendation": "RISK: LOW\n可考慮合併。",
    "outcome": "可考慮合併。",
}


class ReportTests(unittest.TestCase):
    def test_builds_readable_markdown(self) -> None:
        report = build_markdown_report(STATE)
        self.assertIn("# PR 合併前審查報告", report)
        self.assertIn("## LangGraph 平行審查", report)
        self.assertIn("RISK: LOW", report)

    def test_saves_markdown_to_reports_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_path = save_markdown_report(Path(directory), STATE)
            self.assertEqual(report_path.parent.name, "reports")
            self.assertEqual(report_path.suffix, ".md")
            self.assertIn("PR 合併前審查報告", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
