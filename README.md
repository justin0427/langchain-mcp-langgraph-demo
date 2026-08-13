# GitHub PR 合併前檢查助手（Agent 專案）

這是課程中要實作與執行的 **Agent 專案**。它用 LangChain 透過外部 GitHub MCP 蒐集 PR 證據，再用 LangGraph 平行執行程式品質、資安與測試影響檢查，最後決定要人工審查或可考慮合併。

課程會用到兩個 repository，但用途完全不同：

| repository | 何時使用 | 要做什麼 |
| --- | --- | --- |
| `langchain-mcp-langgraph-demo/`（本 repo） | 第 1 步建立後，到課程結束都留在這裡 | 設定 `.env`、貼回 Agent 程式、執行 PR 審查。 |
| `pr-review-lab-你的名字/` | 第 2 步才建立 | 修改小程式、開一個 PR；它只是讓 Agent 審查的目標。 |

**不要把 Agent 程式貼到 PR Lab，也不要在 PR Lab 裡執行 `main.py`。** 取得 PR 編號後，回到本 repo 執行 Agent。

它不包含、自行建立或啟動任何 MCP Server；直接連線到 GitHub 官方遠端 MCP Server 的唯讀 endpoint。

## 專案結構

```text
langchain-mcp-langgraph-demo/
├── .env.example             # 要填入的環境變數範本，不放真實 Token
├── .gitignore               # 避免 .env、虛擬環境與快取被提交
├── requirements.txt          # Python 套件
├── main.py                   # 唯一執行入口：接收 --repo 和 --pr
├── scripts/
│   ├── lab_helper.py          # 課堂清空、checkpoint、預檢與修復工具
│   └── reference/             # 各階段的標準程式碼，供 repair 使用
├── src/
│   ├── config.py             # 讀取 .env、建立 Ollama model、驗證 Token
│   ├── state.py              # PullRequestState 與 reducer 定義
│   ├── github_agent.py       # LangChain Agent + 外部 GitHub MCP 連線
│   ├── nodes.py              # 蒐證、品質、資安、測試、彙整等 Node
│   └── workflow.py           # StateGraph、Edge、條件分流
└── tests/
    └── test_workflow.py      # 不需連 GitHub 的 routing 單元測試
```

## 課堂操作順序

1. **建立與 clone 本 repo**：按 GitHub 的 **Use this template**，命名為 `langchain-mcp-langgraph-demo-你的名字`，clone 到電腦並進入此資料夾。
2. **從本 repo 的文章開始實作 Agent**：建立虛擬環境、設定 `.env`；老師帶做時才執行 `reset --yes`，再依文章貼回 `src/` 與 `main.py`。
3. **建立 PR Lab**：開啟 `https://github.com/justin0427/pr-review-lab-starter`，按 **Use this template** 建立 `pr-review-lab-你的名字`。在那個資料夾修改題目、push、開 PR。
4. **回到本 repo 執行 Agent**：PR 建立後，回到 `langchain-mcp-langgraph-demo-你的名字/`，填入 PR Lab 的 repo 名稱與 PR 編號執行 `run`。

## 設定 Agent

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env       # Windows PowerShell: Copy-Item .env.example .env
```

### 建立 `.env` 需要的 GitHub Token

`GITHUB_TOKEN` 是你在 GitHub 建立的 **fine-grained personal access token（PAT）**，不是從 MCP Server 取得。

1. 開啟 <https://github.com/settings/personal-access-tokens> → **Generate new token**。
2. `Resource owner` 選目標 repository 的 owner；`Repository access` 選 **Only select repositories**，只選要測試的 repository。
3. Repository permissions 全部選 **Read-only**，開啟：`Contents`、`Pull requests`、`Issues`、`Actions`、`Commit statuses`。
4. 按 **Generate token** 後，複製以 `github_pat_` 開頭的完整值，貼到 `.env`：

```dotenv
# 放置檔案：.env
GITHUB_TOKEN=github_pat_你的完整Token貼在這裡
```

選短期有效期限（例如 7 或 30 天），不要把 Token 寫進程式碼、截圖或 Git。若 repository 屬於 Organization，PAT 可能需要管理員核准。完整圖文步驟見 [GitHub 官方文件](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)。

接著把 `LLM_MODEL` 改成已安裝且支援 native tool calling 的 Ollama 模型。完成 `.env` 後先檢查：

```bash
# macOS / Linux
python3 scripts/lab_helper.py check ollama
python3 scripts/lab_helper.py check preflight

# Windows PowerShell
python scripts/lab_helper.py check ollama
python scripts/lab_helper.py check preflight
```

當 PR Lab 的 PR 已建立，**在本 repo 根目錄**執行：

```bash
# macOS / Linux
python3 scripts/lab_helper.py run --repo OWNER/pr-review-lab-你的名字 --pr PR_NUMBER

# Windows PowerShell
python scripts/lab_helper.py run --repo OWNER/pr-review-lab-你的名字 --pr PR_NUMBER
```

## 常見問題

- `Discovered read-only GitHub MCP tools:` 後面沒有工具：確認 PAT、網路與 GitHub MCP URL。
- 模型回答卻沒查 PR：換成支援 tool calling 的模型，並確認 Ollama 正在執行。
- `Connection refused`：啟動 Ollama，或確認 `.env` 的 `OLLAMA_BASE_URL`。
- `GitHub MCP` 回傳 401／403：確認 Token 未過期、Resource owner 正確、已選到目標 repository，且 Organization PAT 已核准。

## 安全邊界

程式使用 `https://api.githubcopilot.com/mcp/readonly` 和 `X-MCP-Readonly: true`，只取得讀取工具；它不會留言、修改 PR 或執行合併。詳見 GitHub 官方文件：<https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp-in-your-ide/set-up-the-github-mcp-server>。

Windows 使用者請將 `python3` 改成 `python` 或本機對應的 Python 指令。
