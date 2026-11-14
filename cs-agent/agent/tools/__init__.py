"""內建工具：直接寫在 Agent 程式裡，不經過 MCP。

每個工具模組都提供兩樣東西：
    SCHEMA：給模型看的工具定義（OpenAI 格式）
    run(**args) -> dict：實際執行
"""

from agent.tools import load_skill, search_policy, transfer

BUILTIN_TOOLS = {
    module.SCHEMA["function"]["name"]: module
    for module in (search_policy, load_skill, transfer)
}
