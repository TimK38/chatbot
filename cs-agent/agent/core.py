"""Agent 的核心迴圈（書上第二章「用程式碼實現 Agent 的核心迴圈」）。

Harness 的主要工作就是管理 messages 這個列表：
    客戶說話 → 加到最後面 → 送給模型
    模型要用工具 → 執行工具 → 結果加到最後面 → 再送給模型
    模型直接回答 → 這一輪結束，等客戶下一句話

messages 只增不改（append-only）：系統提示詞永遠在最前面不動，KV Cache 才能重複利用。
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from openai import AsyncOpenAI

from agent import config
from agent.mcp_client import MCPConnections
from agent.tools import BUILTIN_TOOLS, load_skill

# 迴圈中發生的事，透過這個回呼函式通知外面（main.py 用來印出工具呼叫，評估程式可以拿來記錄）
EventHandler = Callable[[str, dict], None]


@dataclass
class ToolCall:
    """一次工具呼叫的紀錄。評估時用它核對 Agent「實際做了什麼」，不看它「說做了什麼」。"""
    name: str
    args: dict
    result: str
    source: str  # "builtin" 或 MCP 伺服器名稱


def build_system_prompt() -> str:
    template = config.SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{skills_catalog}", load_skill.catalog())


@dataclass
class Agent:
    client: AsyncOpenAI
    model: str
    mcp: MCPConnections
    on_event: EventHandler = lambda kind, data: None
    reasoning_effort: str | None = None

    messages: list[dict[str, Any]] = field(default_factory=list)
    trace: list[ToolCall] = field(default_factory=list)
    ended: bool = False  # 轉接人工後為 True，對話結束

    def __post_init__(self) -> None:
        self.messages = [{"role": "system", "content": build_system_prompt()}]
        self._turn_start = len(self.messages)
        # 工具清單在整段對話中固定不變（也是為了 KV Cache）
        self.tools = [m.SCHEMA for m in BUILTIN_TOOLS.values()] + [t.to_openai() for t in self.mcp.tools.values()]

    # ── 核心迴圈 ─────────────────────────────────────────

    async def respond(self, user_text: str) -> str:
        """處理客戶的一句話，回傳客服的回覆。中間可能呼叫好幾次工具。"""
        if self.ended:
            raise RuntimeError("對話已結束（已轉接真人客服）")
        self._turn_start = len(self.messages)  # 記住這句話開始的位置，出錯時可以退回
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(config.MAX_STEPS_PER_TURN):
            started = time.perf_counter()
            extra = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
            response = await self.client.chat.completions.create(
                model=self.model, messages=self.messages, tools=self.tools, **extra,
            )
            message = response.choices[0].message
            self._report_model_call(response, time.perf_counter() - started)
            # 模型的回覆原封不動加回去（包含 tool_calls，以及 Gemini 附帶的 thought signature 等額外欄位）
            self.messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:  # 沒有要用工具 → 這就是給客戶的回覆
                return message.content or ""

            for call in message.tool_calls:
                result = await self._execute(call.function.name, call.function.arguments)
                self.messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        # 超過上限：多半是卡在重複呼叫工具。不要讓迴圈無限跑下去。
        self.on_event("max_steps", {"limit": config.MAX_STEPS_PER_TURN})
        fallback = "抱歉，系統處理時發生問題，我先幫您轉接真人客服。"
        self.messages.append({"role": "assistant", "content": fallback})
        self.ended = True
        return fallback

    def rollback_turn(self) -> None:
        """模型 API 出錯時，把這句話（以及中途加進去的工具結果）從對話中移除，讓客戶可以重說一次。

        注意：已經執行過的工具（例如 change_plan）不會被復原，它們仍留在 trace 和 audit_log 裡。
        """
        del self.messages[self._turn_start:]

    def _report_model_call(self, response: Any, seconds: float) -> None:
        """回報這次模型呼叫花了多久、用了多少 token（含思考用掉的 token），找出慢在哪裡。"""
        usage = response.usage
        details = getattr(usage, "completion_tokens_details", None) if usage else None
        self.on_event("model_call", {
            "seconds": seconds,
            "tool_calls": len(response.choices[0].message.tool_calls or []),
            "prompt_tokens": usage.prompt_tokens if usage else None,
            "output_tokens": usage.completion_tokens if usage else None,
            "reasoning_tokens": getattr(details, "reasoning_tokens", None) if details else None,
        })

    # ── 執行工具 ─────────────────────────────────────────

    async def _execute(self, name: str, raw_args: str) -> str:
        """執行一個工具，回傳要放進對話的文字。任何錯誤都轉成文字回傳，讓模型看得懂並修正。"""
        try:
            args = json.loads(raw_args or "{}")
        except json.JSONDecodeError:
            args = {}
            result, source = json.dumps({"ok": False, "error": f"參數不是合法的 JSON：{raw_args}"}, ensure_ascii=False), "harness"
        else:
            self.on_event("tool_call", {"name": name, "args": args})
            result, source = await self._dispatch(name, args)

        self.trace.append(ToolCall(name=name, args=args, result=result, source=source))
        self.on_event("tool_result", {"name": name, "result": result})

        if name == "transfer_to_human":
            self.ended = True
        return result

    async def _dispatch(self, name: str, args: dict) -> tuple[str, str]:
        try:
            if name in BUILTIN_TOOLS:
                output = BUILTIN_TOOLS[name].run(**args)
                return json.dumps(output, ensure_ascii=False), "builtin"
            if name in self.mcp.tools:
                return await self.mcp.call(name, args), self.mcp.tools[name].server
            return json.dumps({"ok": False, "error": f"沒有這個工具：{name}"}, ensure_ascii=False), "harness"
        except Exception as exc:  # 參數名稱錯誤、伺服器出錯……都回報給模型，不讓整個 Agent 當掉
            return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), "harness"


def create_agent(
    mcp: MCPConnections,
    model: str | None = None,
    on_event: EventHandler | None = None,
    reasoning_effort: str | None = None,
) -> Agent:
    """建立一個新的 Agent（一段新對話）。評估時每一題都呼叫一次。"""
    api_key = os.environ.get(config.API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"找不到 {config.API_KEY_ENV}，請在 cs-agent/.env 設定")
    client = AsyncOpenAI(api_key=api_key, base_url=config.BASE_URL, max_retries=2)
    return Agent(
        client=client,
        model=model or config.MODEL,
        mcp=mcp,
        on_event=on_event or (lambda k, d: None),
        reasoning_effort=reasoning_effort or config.REASONING_EFFORT,
    )
