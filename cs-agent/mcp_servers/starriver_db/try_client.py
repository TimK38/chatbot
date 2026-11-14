"""MCP 用戶端示範：模擬 Agent 連上 starriver-db 伺服器的完整流程。

用法（在 cs-agent 資料夾執行）：
    python mcp_servers/starriver_db/try_client.py

這支程式做的事，就是 Agent 在「啟動階段」和「使用階段」做的事：
    1. 用 stdio 方式把伺服器程式叫起來
    2. 握手（initialize）
    3. 問伺服器：「你有哪些工具？有哪些資源？」
    4. 實際呼叫幾個工具、讀一個資源
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "server.py"


def show(title: str, result) -> None:
    print(f"\n── {title} ──")
    for block in result.content:
        text = getattr(block, "text", None)
        print(json.dumps(json.loads(text), ensure_ascii=False, indent=2) if text else block)


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])

    # ① 啟動伺服器，兩邊用 stdio 連上
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            # ② 握手
            await session.initialize()

            # ③ 問伺服器有哪些工具、資源
            tools = await session.list_tools()
            print("伺服器提供的工具：")
            for tool in tools.tools:
                first_line = (tool.description or "").strip().splitlines()[0]
                read_only = tool.annotations.read_only_hint if tool.annotations else None
                tag = "唯讀" if read_only else "會改資料"
                print(f"  - [{tag}] {tool.name}: {first_line}")

            resources = await session.list_resources()
            print("伺服器提供的資源：")
            for resource in resources.resources:
                print(f"  - {resource.uri}")

            # ④ 實際呼叫
            show("verify_identity（正確）", await session.call_tool(
                "verify_identity", {"name": "王小明", "phone": "0912-345-678"}))
            show("verify_identity（手機錯誤）", await session.call_tool(
                "verify_identity", {"name": "王小明", "phone": "0912345000"}))
            show("get_viewing_activity", await session.call_tool(
                "get_viewing_activity", {"customer_id": "C001", "days": 30}))

            plans = await session.read_resource("starriver://plans")
            print("\n── 資源 starriver://plans ──")
            print(plans.contents[0].text)


if __name__ == "__main__":
    asyncio.run(main())
