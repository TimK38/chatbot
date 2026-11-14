# skills/ — 處理流程（Agent Skills）

## Skill 跟 Knowledge 的差別

| | `knowledge/` | `skills/` |
|---|---|---|
| 回答的問題 | **規則是什麼？**（事實） | **這件事怎麼做？**（步驟） |
| 例子 | 「年繳開通 14 天內可全額退款」 | 「退款：驗證 → 查開通日 → 查規則 → 確認 → 執行」 |
| Agent 怎麼找到 | `search_policy` **搜尋**相關段落 | 先看**目錄**，再用 `load_skill` 讀整份 |

**Skill 只寫步驟，不寫事實。** 需要用到規則或價格時，Skill 會指向知識庫段落（例如 P3-2）或 `list_plans`，不在 Skill 裡重寫一次，避免同一件事寫在兩個地方而互相矛盾。

## 目前的 Skills

| Skill | 什麼時候用 |
|---|---|
| [cancel-and-refund](cancel-and-refund/SKILL.md) | 取消訂閱、詢問退款、聲稱「之前客服答應退款」 |
| [plan-change](plan-change/SKILL.md) | 升級、降級、詢問哪個方案適合 |
| [pause-and-resume](pause-and-resume/SKILL.md) | 暫停訂閱、恢復訂閱 |
| [billing-dispute](billing-dispute/SKILL.md) | 重複扣款、金額不符、扣款失敗 |

## 格式

每個 Skill 一個資料夾，裡面一份 `SKILL.md`：

```markdown
---
name: cancel-and-refund
description: 什麼時候該用這個 Skill（一兩句話）
---

# 標題
（完整的處理步驟）
```

## Agent 怎麼使用（漸進式披露，第二章、第四章）

```
啟動時：只把每個 Skill 的 name + description 放進系統提示詞（每個幾十 token）
          ↓
對話中：客戶說「我要取消」→ 模型判斷需要 cancel-and-refund
          ↓
        呼叫內建工具 load_skill("cancel-and-refund") → 整份 SKILL.md 加到對話最後面
          ↓
        照著步驟做
```

Skill 全文是**加在對話最後面**，不是插回系統提示詞，這樣前面的 KV Cache 不會失效（只增不改）。

## 安全

這裡的 Skill 都是**純文件**，不附帶任何指令碼，所以載入 Skill 不會執行任何程式。
但 Skill 的內容會直接成為 Agent 的指令，所以**新增或修改 Skill 要像審查程式碼一樣審查**，尤其是從外部取得的 Skill（第四章「第三方能力的安全風險」）。
