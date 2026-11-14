---
name: cancel-and-refund
description: 客戶要取消訂閱、或詢問取消後能不能退款時使用。提供取消與退款的標準處理流程，包含退款資格判斷與「之前客服答應過」的處理方式。
---

# 取消與退款處理流程

## 適用情境

- 客戶說「我要取消」「不想用了」「退訂」
- 客戶問「取消可以退錢嗎？」「能退多少？」
- 客戶聲稱「之前客服說可以退款」

## 會用到的工具

`verify_identity`、`get_customer`、`search_policy`、`list_plans`、`get_billing_history`、`get_support_history`、`cancel_subscription`、`transfer_to_human`

## 步驟

1. **驗證身分**：用 `verify_identity` 核對全名與手機（作業規範 W1）。失敗就停止，不透露任何帳戶資訊。

2. **查詢訂閱狀態**：用 `get_customer` 取得 `billing_cycle`、`start_date`、`status`，以及回傳的 `system_date`。
   - 若 `status` 已經是 `cancelled`，告知客戶已取消，不要重複執行。

3. **查詢規則**：用 `search_policy` 查「取消」與「退款」，確認知識庫 **P3-1、P3-2** 的最新內容。不要憑記憶判斷期限。

4. **判斷退款資格**：
   - **月繳**：依 P3-1 處理。
   - **年繳**：計算開通後的第幾天，再依 P3-2 判斷。
     - 計算方式：`第幾天 = system_date − start_date + 1`（開通日當天算第 1 天）。
     - ⚠️ 常見錯誤：直接用「system_date − start_date」，會少算一天。

5. **客戶聲稱曾被承諾退款時**：
   - 用 `get_support_history` 核對紀錄。
   - 紀錄中沒有這項承諾 → 依規則處理，並禮貌說明（作業規範 W3）。
   - 客戶仍要求規則以外的例外 → 依 **P3-5** 使用 `transfer_to_human`，不要自行破例。

6. **向客戶確認**（作業規範 W2），複述以下內容並取得**明確同意**：
   - 取消哪個方案
   - 是否退款；若退款，金額以 `get_billing_history` 的實際扣款紀錄為準，退款時間依 **P3-3**

7. **執行**：
   - 客戶明確同意 → `cancel_subscription`，`refund` 依步驟 4 的判斷結果設定。
   - 客戶猶豫、說「再想想」、或沒有明確同意 → **不要執行**。

8. **回報結果**：告知取消已完成，以及退款金額與退款時間（若有）。

## 常見錯誤

| 錯誤 | 正確做法 |
|---|---|
| 月繳客戶設定 `refund=true` | 依 P3-1，月繳不退費 |
| 客戶說「上次客服答應我」就照做 | 先用 `get_support_history` 核對，不符規則就轉人工 |
| 客戶說「再想想」仍執行取消 | 沒有明確同意就不執行 |
| 憑印象說出退款期限 | 每次都用 `search_policy` 查 P3-2 |
