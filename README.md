# chatbot

學習 AI Agent 的練習專案。

| 資料夾 | 內容 |
|---|---|
| [cs-agent/](cs-agent/) | 星河影音客服 Agent：有安全防護、能用評估分數衡量好壞（說明見 [cs-agent/README.md](cs-agent/README.md)） |

## 兩台電腦同步

Windows 和 Mac 都用這個 repo，開始前先 `git pull`，結束後 `git add`、`git commit`、`git push`。

**不會進 git 的東西**（每台電腦要自己建）：
- `.env`：放 API key，參考 `cs-agent/.env.example` 自己建一份
- `.venv/`：Python 環境，Windows 和 Mac 不能共用
- `cs-agent/mcp_servers/*/runtime/`：資料庫檔，用 `init_db.py` 重新產生
