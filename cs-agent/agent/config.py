"""Agent 的設定：用哪個模型、去哪裡找知識和 Skills、要連哪些 MCP 伺服器。

所有「可以換」的東西都集中在這裡，其他檔案只負責邏輯。
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent  # cs-agent/
AGENT_DIR = ROOT / "agent"

# .env 只放密鑰，不進 git。已經設在環境變數裡的值優先（load_dotenv 不會覆蓋）。
load_dotenv(ROOT / ".env")

# ── 模型 ─────────────────────────────────────────────────
# 用 OpenAI 相容的 API 格式（跟書上第二章的程式碼一樣），
# Gemini 有提供這種相容介面，所以只要換 base_url 和 key 就能用。
# 想換模型時，在 .env 加一行 AGENT_MODEL=... 即可，不必改程式。
MODEL = os.environ.get("AGENT_MODEL", "gemini-3.5-flash")
BASE_URL = os.environ.get("AGENT_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
API_KEY_ENV = "GEMINI_API_KEY"

# 思考程度：Gemini 3.x 是「會先思考再回答」的模型，思考越多越慢。
# 可設 minimal / low / medium / high；不設（None）就用模型預設值。
# 調低可以變快，但可能比較容易出錯 —— 要用評估分數決定，不要用感覺決定。
REASONING_EFFORT = os.environ.get("AGENT_REASONING_EFFORT") or None

# 客戶說一句話之後，Agent 最多連續呼叫幾次模型（防止卡在同一個工具反覆呼叫，書上第二章提醒過）。
MAX_STEPS_PER_TURN = 15

# ── 提示詞、知識、Skills ──────────────────────────────────
SYSTEM_PROMPT_PATH = AGENT_DIR / "prompts" / "system.md"
KNOWLEDGE_DIR = ROOT / "knowledge" / "policies"
SKILLS_DIR = ROOT / "skills"

# ── MCP 伺服器 ────────────────────────────────────────────
# key 是「客戶端自己取的名字」（learning-notes 第二節第 3 點），用來記錄與除錯。
# env_passthrough：只把列出的環境變數傳給伺服器。
#   沒列出的（例如 GEMINI_API_KEY）伺服器就拿不到，這是「最小權限」。
#   STARRIVER_DB 讓評估程式可以換成拋棄式的資料庫副本。
#
# 兩種連線方式（learning-notes 第二節第 3 點）：
#   有 "command" → stdio：在本機把伺服器程式叫起來，用 stdin / stdout 對話
#   有 "url"     → Streamable HTTP：伺服器跑在別人的機器上，我們透過網路呼叫
# allowed_tools（選填）：只讓模型看到列出的工具。伺服器提供什麼，不等於模型就該看到什麼。
MCP_SERVERS = {
    # 內部伺服器（stdio）：我們自己寫的，資料庫也在它那裡
    "starriver_db": {
        "command": sys.executable,
        "args": [str(ROOT / "mcp_servers" / "starriver_db" / "server.py")],
        "env_passthrough": ["STARRIVER_DB"],
    },
    # 外部伺服器（Streamable HTTP）：Microsoft 官方營運的 Learn 文件搜尋
    # 用途：客戶問 Windows / Edge / Xbox 等微軟產品上的播放設定問題時，查官方文件回答。
    # - 不需要帳號或 key：我們沒有任何密鑰交給它
    # - 只開放 microsoft_docs_search：能力越少，風險越小
    # - 注意：送出的查詢字串會被 Microsoft 收到，所以不能把客戶資料放進查詢（作業規範 W7）
    # - 回傳的內容是外部資料，跟資料庫的 notes 一樣不可信（W6）
    "microsoft_learn": {
        "url": "https://learn.microsoft.com/api/mcp",
        "allowed_tools": ["microsoft_docs_search"],
    },
}
