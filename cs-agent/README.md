# 星河影音 客服 Agent（學習專案）

邊讀《AI Agent》邊動手做的練習專案：一個有安全防護、能用數字衡量好壞的客服 Agent。

完整規格見 [docs/spec.md](docs/spec.md)，學習筆記與規劃見 [docs/learning-notes.md](docs/learning-notes.md)。

## 資料夾結構

資料夾依照 Agent 的架構元件來分（**Agent = Model + Harness**）：

```
cs-agent/
├── docs/spec.md          規格書
├── agent/                【Harness】Agent 本體：核心迴圈、系統提示詞、內建工具（步驟 2）
├── knowledge/policies/   【知識】產品規則（事實），給 search_policy 搜尋
├── skills/               【流程】處理步驟（Agent Skills），給 load_skill 載入
├── mcp_servers/          【外部工具】每個 MCP 伺服器一個資料夾，自給自足
│   └── starriver_db/       客戶資料庫伺服器（資料庫也在這裡，runtime/ 不進 git）
├── evals/                【評估】題目、評估程式、結果
└── notebooks/            開發者的資料探索
```

## 快速開始

需要 [uv](https://docs.astral.sh/uv/)（用來安裝 Python 3.12）。在 `cs-agent` 資料夾執行：

**macOS**
```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env                                  # 然後填入 GEMINI_API_KEY

.venv/bin/python mcp_servers/starriver_db/init_db.py  # 建立（或重置）資料庫
.venv/bin/python mcp_servers/starriver_db/try_client.py  # 模擬 Agent 連上 MCP 伺服器
.venv/bin/python -m agent.main --reset-db             # 跟客服 Agent 對話（你扮演客戶）
```

**Windows**
```
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
copy .env.example .env                                :: 然後填入 GEMINI_API_KEY

.venv\Scripts\python.exe mcp_servers\starriver_db\init_db.py
.venv\Scripts\python.exe mcp_servers\starriver_db\try_client.py
.venv\Scripts\python.exe -m agent.main --reset-db
```

資料探索：用 VS Code 打開 `notebooks/eda.ipynb`，Kernel 選 `cs-agent/.venv`。

## 進度

| 步驟 | 內容 | 狀態 |
|---|---|---|
| 0 | 規格：情境、規則、資料、工具 | ✅ |
| 1 | 評估題目 17 題 | ✅ |
| — | 資料庫 + MCP 伺服器 | ✅ |
| 2 | 最小 Agent（核心迴圈 + 工具） | ✅ |
| 3 | 評估程式：重置 → 執行 → 核對 → 算分 | ⬜ |
| 4 | 加安全防護，每次只改一項，比較分數 | ⬜ |
| 5 | 失敗歸因，把失敗變成新題目 | ⬜ |
