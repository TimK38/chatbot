-- 星河影音 客服資料庫結構（SQLite）
-- 每次執行 init_db.py 都會刪掉舊表、重新建立，確保每一題評估都從同一個起點開始。

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS viewing_history;
DROP TABLE IF EXISTS billing_records;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS plans;
DROP TABLE IF EXISTS meta;

-- 系統設定（例如固定的系統日期）
CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 方案目錄
CREATE TABLE plans (
    plan_id       TEXT PRIMARY KEY,           -- basic / standard / premium
    name_zh       TEXT NOT NULL,
    tier          INTEGER NOT NULL,           -- 等級，數字越大越高級
    monthly_price INTEGER NOT NULL,
    yearly_price  INTEGER NOT NULL,
    max_devices   INTEGER NOT NULL,           -- 同時觀看裝置數
    max_quality   TEXT NOT NULL
);

-- 客戶基本資料
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    phone       TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    notes       TEXT NOT NULL DEFAULT ''      -- 內部備註（自由文字，不可信）
);

-- 訂閱狀態（一位客戶一筆）
CREATE TABLE subscriptions (
    customer_id           TEXT PRIMARY KEY REFERENCES customers(customer_id),
    plan_id               TEXT NOT NULL REFERENCES plans(plan_id),
    billing_cycle         TEXT NOT NULL CHECK (billing_cycle IN ('monthly', 'yearly')),
    status                TEXT NOT NULL CHECK (status IN ('active', 'paused', 'cancelled')),
    start_date            TEXT NOT NULL,
    next_billing_date     TEXT,
    pending_plan          TEXT REFERENCES plans(plan_id),
    paused_until          TEXT,
    pause_count_this_year INTEGER NOT NULL DEFAULT 0,
    refunded              INTEGER NOT NULL DEFAULT 0      -- 0 / 1
);

-- 付款紀錄
CREATE TABLE billing_records (
    record_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    billed_at   TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('success', 'failed', 'refunded')),
    description TEXT NOT NULL
);

-- 觀看紀錄（使用者行為資料）
CREATE TABLE viewing_history (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    watched_at  TEXT NOT NULL,
    device_type TEXT NOT NULL CHECK (device_type IN ('tv', 'phone', 'tablet', 'pc')),
    device_name TEXT NOT NULL,
    title       TEXT NOT NULL,
    minutes     INTEGER NOT NULL,
    quality     TEXT,                                   -- 被擋下時為 NULL
    event       TEXT NOT NULL CHECK (event IN ('play', 'blocked_concurrent_limit'))
);

-- 歷史客服紀錄
CREATE TABLE support_tickets (
    ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    created_at  TEXT NOT NULL,
    channel     TEXT NOT NULL,
    summary     TEXT NOT NULL,
    resolution  TEXT NOT NULL
);

-- Agent 的每一次工具呼叫都記在這裡（稽核用，評估時也可以拿來核對）
CREATE TABLE audit_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    tool        TEXT NOT NULL,
    customer_id TEXT,
    args_json   TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
