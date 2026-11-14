"""內建工具 transfer_to_human：轉接真人客服。

這是學習專案，沒有真的真人客服系統，所以這裡只回傳「已轉接」。
真正讓對話結束的是 Harness（core.py 看到這個工具被呼叫，就把 agent.ended 設成 True），
不是靠模型自己記得要停。
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "transfer_to_human",
        "description": (
            "轉接真人客服，呼叫後對話即結束。只在知識庫 P3-5 列出的情況使用"
            "（帳務爭議、要求規則以外的例外、正式投訴、疑似盜用）；呼叫前可先用 search_policy 查 P3-5。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "轉接原因，要寫出具體事實（日期、金額、客戶的要求），讓真人客服不必重問",
                },
            },
            "required": ["reason"],
        },
    },
}


def run(reason: str) -> dict:
    return {
        "ok": True,
        "transferred": True,
        "message": "已轉接真人客服。請用一兩句話告知客戶已轉接，並說明真人客服會接手處理；不要再呼叫其他工具。",
    }
