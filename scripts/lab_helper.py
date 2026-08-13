"""課堂實作輔助工具：清空指定檔案、檢查每個階段、啟動完整流程。"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import os
from pathlib import Path
import subprocess
import sys
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import json


ROOT = Path(__file__).resolve().parent.parent
# 腳本從 scripts/ 執行時，先把專案根目錄加入 import 路徑，才能讀到 src/。
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
AGENT_FILES = (
    "main.py",
    "src/config.py",
    "src/state.py",
    "src/github_agent.py",
    "src/nodes.py",
    "src/workflow.py",
)
REFERENCE_DIR = ROOT / "scripts" / "reference"
REPAIR_FILES: dict[str, tuple[str, ...]] = {
    "config": ("src/config.py",),
    "state": ("src/state.py",),
    "mcp": ("src/github_agent.py",),
    "nodes": ("src/nodes.py",),
    "workflow": ("src/workflow.py",),
    "main": ("main.py",),
}
REQUIRED_PATHS = (*AGENT_FILES, "app", "tests", ".env.example", "requirements.txt", "scripts/reference")


def ok(message: str) -> None:
    print(f"✅ {message}")


def command_name() -> str:
    """依平台顯示學生可以直接複製的 Python 指令。"""
    return "python" if os.name == "nt" else "python3"


def fail(stage: str, error: Exception, repair_stage: str | None = None) -> None:
    print(f"❌ {stage} 尚未通過：{error}")
    detail = str(error)
    if isinstance(error, ModuleNotFoundError):
        print("   找不到套件：請確認已啟用虛擬環境，並執行 pip install -r requirements.txt。")
    elif isinstance(error, FileNotFoundError):
        print("   專案路徑或檔案不完整：請確認是在 Template 專案中執行，且沒有刪掉檔案。")
        print("   Agent 檔案遺失時可執行 repair all --yes；其他檔案遺失請重新從 Template 建立專案。")
    elif "Ollama" in detail:
        print("   Ollama 有問題：先執行 ollama list；若連不上，請開啟 Ollama App 或執行 ollama serve。")
        print("   模型不存在時，請執行 ollama pull <LLM_MODEL>，再確認 .env 的 LLM_MODEL 名稱。")
    elif "GITHUB_TOKEN" in detail or "GitHub MCP returned no tools" in detail:
        print("   GitHub MCP 設定或網路有問題：請檢查 .env、PAT 權限、MCP URL 與網路。")
    elif isinstance(error, SyntaxError) or "cannot import name" in detail:
        if repair_stage:
            print("   偵測到程式碼可能漏貼、貼錯位置或打字錯誤。")
            print(
                f"   要還原本階段的標準版本，執行："
                f"{command_name()} scripts/lab_helper.py repair {repair_stage} --yes"
            )
    elif repair_stage:
        print("   可能是程式碼漏貼、貼錯位置或打字錯誤。")
        print(
            f"   要還原本階段的標準版本，執行："
            f"{command_name()} scripts/lab_helper.py repair {repair_stage} --yes"
        )
    else:
        print("   請檢查本階段上方的設定與指令，再重新執行 checkpoint。")
    raise SystemExit(1)


def check_tests() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("單元測試失敗")
    ok("calculate_total 測試通過")


def check_paths() -> None:
    """先確認學生是在完整的 Template 專案裡執行腳本。"""
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise FileNotFoundError("找不到：" + ", ".join(missing))
    ok("專案路徑與必要檔案完整")


def check_setup() -> None:
    for package in ("langchain", "langgraph", "dotenv"):
        importlib.import_module(package)
    ok("Python 套件已安裝")


def check_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        raise RuntimeError("找不到 .env；請先由 .env.example 複製建立")

    from dotenv import load_dotenv

    load_dotenv(env_file, override=True)
    if not os.environ.get("LLM_MODEL"):
        raise RuntimeError("LLM_MODEL 尚未設定")
    if not os.environ.get("GITHUB_TOKEN", "").startswith("github_pat_"):
        raise RuntimeError("GITHUB_TOKEN 尚未填入 fine-grained PAT")
    # 不印出 Token，只說明檢查結果。
    ok(".env 已設定完成")


def check_ollama() -> None:
    """檢查 Ollama 是否啟動，以及 .env 指定的模型是否已下載。"""
    from dotenv import load_dotenv

    env_file = ROOT / ".env"
    if not env_file.is_file():
        raise RuntimeError("Ollama 檢查前需要先建立 .env")
    load_dotenv(env_file, override=True)
    model = os.environ.get("LLM_MODEL", "")
    if not model:
        raise RuntimeError("Ollama 檢查前需要先設定 LLM_MODEL")

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    try:
        with urlopen(f"{base_url}/api/tags", timeout=5) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"Ollama 伺服器連不上（{base_url}）：{error}") from error

    installed_models = {item.get("name", "") for item in payload.get("models", [])}
    if model not in installed_models:
        available = ", ".join(sorted(installed_models)) or "沒有已下載模型"
        raise RuntimeError(
            f"Ollama 找不到 LLM_MODEL={model}；目前可用模型：{available}"
        )
    ok(f"Ollama 已啟動，模型 {model} 可使用")


def import_module(module_name: str, message: str) -> None:
    importlib.import_module(module_name)
    ok(message)


def check_syntax(relative_path: str) -> None:
    """只檢查語法，不建立 __pycache__，避免教室電腦的權限問題。"""
    path = ROOT / relative_path
    compile(path.read_text(encoding="utf-8"), str(path), "exec")


def check_config() -> None:
    import_module("src.config", "config.py 可以被匯入")


def check_state() -> None:
    import_module("src.state", "PullRequestState 可以被匯入")


def check_mcp() -> None:
    from src.github_agent import build_evidence_agent

    # 只讀 GitHub MCP；成功時會列出工具，但不會寫入 GitHub。
    asyncio.run(build_evidence_agent())
    ok("外部 GitHub MCP 連線成功")


def check_nodes() -> None:
    check_syntax("src/nodes.py")
    import_module("src.nodes", "nodes.py 語法與匯入檢查通過")


def check_workflow() -> None:
    check_syntax("src/workflow.py")
    from src.workflow import build_workflow

    build_workflow()
    ok("LangGraph 工作流編譯成功")


def check_main() -> None:
    check_syntax("main.py")
    ok("main.py 語法檢查通過")


CHECKS: dict[str, tuple[str, Callable[[], None]]] = {
    "paths": ("專案路徑", check_paths),
    "tests": ("小程式測試", check_tests),
    "setup": ("Python 套件", check_setup),
    "env": (".env", check_env),
    "ollama": ("Ollama", check_ollama),
    "config": ("config.py", check_config),
    "state": ("State", check_state),
    "mcp": ("外部 GitHub MCP", check_mcp),
    "nodes": ("審查 Node", check_nodes),
    "workflow": ("LangGraph 工作流", check_workflow),
    "main": ("main.py", check_main),
}


def reset_agent_files(confirmed: bool) -> None:
    if not confirmed:
        raise RuntimeError("此操作會清空 Agent 檔案；請加上 --yes 確認")
    for relative_path in AGENT_FILES:
        (ROOT / relative_path).write_text("", encoding="utf-8")
    ok("已清空 6 個 Agent 檔案；現在可依文章順序貼回程式碼")


def repair_stage(stage: str, confirmed: bool) -> None:
    """將指定 Agent 檔案還原成課堂的正確版本。"""
    if not confirmed:
        raise RuntimeError("此操作會覆蓋目前程式碼；請加上 --yes 確認")

    stages = tuple(REPAIR_FILES) if stage == "all" else (stage,)
    for stage_name in stages:
        for relative_path in REPAIR_FILES[stage_name]:
            source = REFERENCE_DIR / relative_path
            target = ROOT / relative_path
            if not source.is_file():
                raise RuntimeError(f"找不到修復範本：{source.relative_to(ROOT)}")
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    ok("已還原課堂標準版本；請重新執行對應的 check 指令")


def run_checks(stage: str) -> None:
    if stage == "all":
        names = tuple(CHECKS)
    elif stage == "preflight":
        names = ("paths", "setup", "env", "ollama", "config", "state", "nodes", "workflow", "main", "mcp")
    else:
        names = (stage,)
    for name in names:
        label, checker = CHECKS[name]
        try:
            checker()
        except Exception as error:  # 顯示學生可直接理解的階段與錯誤。
            fail(label, error, name if name in REPAIR_FILES else None)


def run_workflow(repo: str, pull_number: int) -> None:
    if repo.count("/") != 1:
        raise RuntimeError("--repo 必須是 OWNER/REPO 格式，例如 amy/pr-review-lab-amy")
    print("--- 執行前預檢：路徑、套件、.env、Ollama、程式碼與 GitHub MCP ---")
    run_checks("preflight")
    command = [sys.executable, "main.py", "--repo", repo, "--pr", str(pull_number)]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        print("❌ 完整流程失敗；請先執行 check ollama 或 check mcp，確認模型與 GitHub MCP。")
    raise SystemExit(result.returncode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LangChain + MCP + LangGraph 課堂實作助手")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reset = subparsers.add_parser("reset", help="清空六個 Agent 檔案，準備跟著課堂實作")
    reset.add_argument("--yes", action="store_true", help="確認清空檔案內容")

    repair = subparsers.add_parser("repair", help="用課堂標準版本覆蓋出錯的 Agent 檔案")
    repair.add_argument("stage", choices=(*REPAIR_FILES, "all"))
    repair.add_argument("--yes", action="store_true", help="確認覆蓋目前程式碼")

    check = subparsers.add_parser("check", help="檢查目前實作階段")
    check.add_argument("stage", choices=(*CHECKS, "all", "preflight"))

    run = subparsers.add_parser("run", help="執行完整 PR 審查工作流")
    run.add_argument("--repo", required=True, help="GitHub repository，格式為 OWNER/REPO")
    run.add_argument("--pr", required=True, type=int, help="Pull Request 編號")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "reset":
        try:
            reset_agent_files(args.yes)
        except RuntimeError as error:
            fail("清空檔案", error)
    elif args.command == "repair":
        try:
            repair_stage(args.stage, args.yes)
        except RuntimeError as error:
            fail("修復程式碼", error)
    elif args.command == "check":
        run_checks(args.stage)
    else:
        try:
            run_workflow(args.repo, args.pr)
        except RuntimeError as error:
            fail("完整 PR 審查", error)


if __name__ == "__main__":
    main()
