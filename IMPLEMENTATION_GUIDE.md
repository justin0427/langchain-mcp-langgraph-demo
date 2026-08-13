# 課堂實作指南

這份指南只處理 **Agent 專案** `langchain-mcp-langgraph-demo-你的名字/`。請先把它 clone 到電腦；不要在這裡修改 `price_calculator.py`，那是另一個 PR Lab 專案的工作。

## 兩個 repository 的固定分工

| 你現在所在的位置 | 你在做什麼 | 下一步會去哪裡？ |
| --- | --- | --- |
| `langchain-mcp-langgraph-demo-你的名字/` | 實作與執行 LangChain + MCP + LangGraph Agent | 要開 PR 時才切去 PR Lab。 |
| `pr-review-lab-你的名字/` | 修改小程式、push、在 GitHub 開 PR | PR 建立後立刻回到 Agent 專案。 |

## 檔案已經都在，不要自己新增檔案

Template 已經提供 `src/`、`main.py` 與 `scripts/`。老師帶實作時，先在 **Agent 專案根目錄**執行一次：

```bash
# macOS / Linux
python3 scripts/lab_helper.py reset --yes

# Windows PowerShell
python scripts/lab_helper.py reset --yes
```

這會清空六個 Agent 檔案的內容，讓大家同步貼程式；資料夾和檔案都還在。每貼完一個階段，使用文章裡緊接著的 checkpoint 指令。貼錯或漏貼時可還原標準版本：

```bash
# macOS / Linux：以 nodes 為例
python3 scripts/lab_helper.py repair nodes --yes
python3 scripts/lab_helper.py check nodes

# Windows PowerShell：以 nodes 為例
python scripts/lab_helper.py repair nodes --yes
python scripts/lab_helper.py check nodes
```

可修復階段：`config`、`state`、`mcp`、`nodes`、`workflow`、`main`；整段都要還原時使用 `repair all --yes`。

## 程式碼放置順序

| 順序 | 完整貼到哪個檔案 | 這段在做什麼 | Checkpoint |
| --- | --- | --- | --- |
| 1 | `.env` | Ollama、GitHub PAT、外部 GitHub MCP endpoint | `check env`、`check ollama` |
| 2 | `src/config.py` | 讀取環境設定、建立模型 | `check config` |
| 3 | `src/state.py` | 定義整張工作單 State | `check state` |
| 4 | `src/github_agent.py` | 連外部 MCP，建立 LangChain 蒐證 Agent | `check mcp` |
| 5 | `src/nodes.py` | 蒐證、三個平行審查、彙整報告 | `check nodes` |
| 6 | `src/workflow.py` | 接 Node 與 Edge 成 LangGraph | `check workflow` |
| 7 | `main.py` | 接收 PR 參數並印出結果 | `check main` |

## 最後執行的位置

PR Lab 已開出 PR 後，從 GitHub URL 找到 repository 與編號，例如：

```text
https://github.com/amy/pr-review-lab-amy/pull/3
```

回到 **Agent 專案**根目錄執行：

```bash
# macOS / Linux
python3 scripts/lab_helper.py run --repo amy/pr-review-lab-amy --pr 3

# Windows PowerShell
python scripts/lab_helper.py run --repo amy/pr-review-lab-amy --pr 3
```

不要在 `pr-review-lab-你的名字/` 執行這段指令；那個專案只有被審查的程式與 PR。
