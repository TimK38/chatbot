"""MCP 用戶端：連上設定裡的所有 MCP 伺服器（本機 stdio 或遠端 HTTP），並把它們的工具轉成模型看得懂的格式。

流程跟 try_client.py 一樣（initialize → tools/list → tools/call），
差別在於這裡要「長時間連著」，讓 Agent 在整段對話中都能呼叫工具。
"""

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
import os
from typing import AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client
from mcp.client.streamable_http import streamable_http_client


@dataclass
class MCPTool:
    server: str           # 來自哪個伺服器（config.MCP_SERVERS 的 key）
    name: str
    description: str
    input_schema: dict
    read_only: bool       # 伺服器自己標的「唯讀」。只是說明，不是鎖（learning-notes 第二節第 3 點）

    def to_openai(self) -> dict:
        """轉成 OpenAI 格式的工具定義（書上第二章 tools 清單的格式）。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


class MCPConnections:
    """持有所有 MCP 連線，提供「列工具」和「呼叫工具」兩個動作。"""

    def __init__(self) -> None:
        self.tools: dict[str, MCPTool] = {}
        self._sessions: dict[str, ClientSession] = {}

    async def _connect(self, stack: AsyncExitStack, key: str, cfg: dict) -> None:
        # 兩種連線方式只差在「怎麼建立管道」；建好之後都是一對 (read, write)，後面的用法完全一樣
        if "url" in cfg:
            # Streamable HTTP：連到別人機器上的伺服器
            transport = streamable_http_client(cfg["url"])
        else:
            # stdio：在本機啟動伺服器程式
            env = get_default_environment()  # 只有 HOME、PATH 這類基本變數
            for var in cfg.get("env_passthrough", []):
                if var in os.environ:
                    env[var] = os.environ[var]
            transport = stdio_client(StdioServerParameters(command=cfg["command"], args=cfg["args"], env=env))

        read, write = await stack.enter_async_context(transport)
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()  # 握手
        self._sessions[key] = session

        listed = await session.list_tools()
        allowed = cfg.get("allowed_tools")  # None 代表全部開放
        for t in listed.tools:
            if allowed is not None and t.name not in allowed:
                continue  # 伺服器有提供，但我們不讓模型看到
            if t.name in self.tools:
                raise RuntimeError(f"工具名稱重複：{t.name}（{key} 與 {self.tools[t.name].server}）")
            self.tools[t.name] = MCPTool(
                server=key,
                name=t.name,
                description=(t.description or "").strip(),
                input_schema=t.input_schema,
                read_only=bool(t.annotations and t.annotations.read_only_hint),
            )

    async def call(self, name: str, arguments: dict) -> str:
        """呼叫工具，回傳文字結果（直接放進對話給模型看）。"""
        tool = self.tools[name]
        result = await self._sessions[tool.server].call_tool(name, arguments)
        text = "\n".join(getattr(block, "text", str(block)) for block in result.content)
        return f"[工具執行錯誤] {text}" if result.is_error else text


@asynccontextmanager
async def connect_mcp(servers: dict[str, dict]) -> AsyncIterator[MCPConnections]:
    """用法：async with connect_mcp(config.MCP_SERVERS) as mcp: ...

    離開 with 區塊時，所有伺服器程序會自動關閉。
    """
    async with AsyncExitStack() as stack:
        conns = MCPConnections()
        for key, cfg in servers.items():
            await conns._connect(stack, key, cfg)
        yield conns
