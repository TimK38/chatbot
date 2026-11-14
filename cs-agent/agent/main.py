"""在終端機跟客服 Agent 對話（你扮演客戶）。

用法（在 cs-agent 資料夾執行）：
    .venv/bin/python -m agent.main              # 一般對話，會顯示工具呼叫
    .venv/bin/python -m agent.main --reset-db   # 先把資料庫重置成初始資料
    .venv/bin/python -m agent.main --quiet      # 不顯示工具呼叫

輸入 exit 或按 Ctrl+D 結束。
"""

import argparse
import asyncio
import json
import time

import openai

from agent import config
from agent.core import create_agent
from agent.mcp_client import connect_mcp

DIM, CYAN, YELLOW, RESET = "\033[2m", "\033[36m", "\033[33m", "\033[0m"


def _short(text: str, limit: int = 300) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "…"


def print_event(kind: str, data: dict) -> None:
    if kind == "tool_call":
        args = json.dumps(data["args"], ensure_ascii=False)
        print(f"{YELLOW}  ⚙ {data['name']}({args}){RESET}")
    elif kind == "tool_result":
        print(f"{DIM}    → {_short(data['result'])}{RESET}")
    elif kind == "model_call":
        thinking = f"，思考 {data['reasoning_tokens']}" if data["reasoning_tokens"] else ""
        action = f"→ 呼叫 {data['tool_calls']} 個工具" if data["tool_calls"] else "→ 回覆客戶"
        print(f"{DIM}  ⏱ 模型 {data['seconds']:.1f}s（輸入 {data['prompt_tokens']}、輸出 {data['output_tokens']}{thinking} tokens）{action}{RESET}")
    elif kind == "max_steps":
        print(f"{YELLOW}  ⚠ 超過每輪 {data['limit']} 次模型呼叫的上限{RESET}")


async def chat(model: str | None, quiet: bool, effort: str | None) -> None:
    async with connect_mcp(config.MCP_SERVERS) as mcp:
        agent = create_agent(mcp, model=model, on_event=None if quiet else print_event, reasoning_effort=effort)
        print(f"{DIM}模型：{agent.model}｜思考程度：{agent.reasoning_effort or '預設'}｜工具：{len(agent.tools)} 個（輸入 exit 結束）{RESET}\n")

        while not agent.ended:
            try:
                user_text = (await asyncio.to_thread(input, "客戶> ")).strip()
            except EOFError:
                break
            if user_text.lower() in {"exit", "quit"}:
                break
            if not user_text:
                continue
            started = time.perf_counter()
            try:
                reply = await agent.respond(user_text)
            except openai.APIStatusError as exc:
                # 例如 429（免費額度用完或太頻繁）。印出原因，不讓整個程式當掉。
                hint = "：免費額度用完或請求太頻繁，請稍後再試" if exc.status_code == 429 else ""
                print(f"{YELLOW}  ⚠ 模型 API 錯誤 {exc.status_code}{hint}{RESET}\n")
                # 這句話沒有得到回覆，從對話中移除，避免下一句話時出現兩筆連續的 user 訊息
                agent.rollback_turn()
                continue
            print(f"{CYAN}客服> {reply}{RESET}")
            if not quiet:
                print(f"{DIM}  （這句話共花 {time.perf_counter() - started:.1f}s）{RESET}")
            print()

        if agent.ended:
            print(f"{DIM}（已轉接真人客服，對話結束）{RESET}")
        print(f"{DIM}本次對話共呼叫工具 {len(agent.trace)} 次：{', '.join(c.name for c in agent.trace) or '無'}{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="星河影音客服 Agent")
    parser.add_argument("--model", help=f"要用的模型（預設 {config.MODEL}）")
    parser.add_argument("--reset-db", action="store_true", help="開始前把資料庫重置成初始資料")
    parser.add_argument("--quiet", action="store_true", help="不顯示工具呼叫")
    parser.add_argument("--effort", choices=["minimal", "low", "medium", "high"],
                        help="模型的思考程度（越低越快，但可能比較容易出錯）")
    args = parser.parse_args()

    if args.reset_db:
        # 這裡是「開發者」在重置資料，不是 Agent 在讀資料庫，所以可以直接呼叫 init_db
        import runpy
        runpy.run_path(str(config.ROOT / "mcp_servers" / "starriver_db" / "init_db.py"), run_name="__main__")

    try:
        asyncio.run(chat(args.model, args.quiet, args.effort))
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
