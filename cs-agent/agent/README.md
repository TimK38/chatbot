# agent/ — 客服 Agent 本體（Harness）

```
agent/
├── main.py            在終端機跟 Agent 對話（你扮演客戶）
├── core.py            核心迴圈（第二章的 while 迴圈）＋ 工具呼叫軌跡 trace
├── config.py          模型設定、知識與 Skills 的位置、要連哪些 MCP 伺服器
├── mcp_client.py      啟動 MCP 伺服器、列工具、呼叫工具
├── prompts/
│   └── system.md      系統提示詞：作業規範 W1～W7 ＋ Skills 目錄（{skills_catalog} 啟動時填入）
└── tools/             內建工具（每個模組提供 SCHEMA 和 run()）
    ├── search_policy.py     搜尋 knowledge/policies/（依 ## 切段，中文兩字一組比對）
    ├── load_skill.py        載入 skills/<name>/SKILL.md 全文（只接受目錄裡有的名字）
    └── transfer.py          轉接真人客服（Harness 看到後把 agent.ended 設成 True）
```

## 執行

在 `cs-agent` 資料夾：

```
.venv/bin/python -m agent.main --reset-db
```

模型預設 `gemini-3.5-flash`，透過 Gemini 的 OpenAI 相容介面呼叫（跟書上第二章的程式碼同一種格式）。
要換模型：在 `.env` 加 `AGENT_MODEL=...`，或執行時加 `--model ...`。

## 一句話的處理流程

```
客戶說話 → messages 最後面加一筆 user
  ┌─▶ 送給模型（system + 全部歷史 + 工具清單）
  │     模型要用工具 → 執行 → 結果加在最後面（role: tool）─┐
  └──────────────────────────────────────────────────────┘
        模型直接回答 → 回傳給客戶，等下一句
```

- **只增不改**：系統提示詞和工具清單在整段對話中固定，Skill 全文以工具結果加在最後面，KV Cache 不會失效。
- **每輪上限** `MAX_STEPS_PER_TURN = 15`：避免卡在重複呼叫工具。超過就轉人工。
- **錯誤不當掉**：參數錯、工具不存在、伺服器出錯，都轉成文字回給模型，讓它自己修正。
- **trace**：`agent.trace` 記錄每一次工具呼叫（包含內建工具）。伺服器的 `audit_log` 看不到 `search_policy`、`transfer_to_human`，評估程式要用 trace 核對。

## 連接的 MCP 伺服器

| 名稱 | 連線方式 | 跑在哪裡 | 開放給模型的工具 |
|---|---|---|---|
| `starriver_db` | stdio | 你的電腦（我們自己寫的） | 全部 10 個 |
| `microsoft_learn` | Streamable HTTP | Microsoft 的機器（`https://learn.microsoft.com/api/mcp`） | 只有 `microsoft_docs_search` |

外部伺服器的選擇原則：大公司官方營運、不需要帳號或 key、工具標為唯讀；只開放需要的工具。
**送出去的參數就是外洩的管道**：查詢字串會被 Microsoft 收到，所以系統提示詞加了 W7（不得放客戶資料）。
目前 W7 只是提示詞規則，不是鎖；步驟 4 可以在 Harness 檢查送往外部的參數。

## 安全邊界

- Agent 只能透過 MCP 工具存取客戶資料，**不直接讀資料庫檔**。
- MCP 伺服器只會拿到 `HOME`、`PATH` 這類基本環境變數，加上 `config.py` 列出的 `STARRIVER_DB`，**拿不到 `GEMINI_API_KEY`**（最小權限）。
- `load_skill` 只接受目錄裡有的名字，傳 `../../.env` 這類路徑會被拒絕。
- 目前所有規則（W1～W7）都還只寫在提示詞裡，靠模型自己遵守。步驟 4 再把部分規則搬到模型碰不到的地方。
