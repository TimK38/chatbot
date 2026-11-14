"""建立（或重置）星河影音的 SQLite 資料庫。

用法（在 cs-agent 資料夾執行）：
    python mcp_servers/starriver_db/init_db.py

每次執行都會刪掉舊資料、依 schema.sql 重建資料表，再匯入 seed.json。
產生的資料庫檔放在 runtime/starriver.db（執行時產生，不進 git）。
評估時，每一題開始前都會呼叫 init_db()，確保所有題目從同一個起點開始。
"""

import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "runtime" / "starriver.db"
SCHEMA_PATH = HERE / "schema.sql"
SEED_PATH = HERE / "seed.json"


def _insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    """把一組 dict 寫進指定的資料表（欄位名稱 = dict 的 key）。"""
    for row in rows:
        columns = ", ".join(row.keys())
        placeholders = ", ".join("?" for _ in row)
        conn.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            list(row.values()),
        )


def init_db(db_path: Path = DB_PATH, seed_path: Path = SEED_PATH) -> Path:
    seed = json.loads(seed_path.read_text(encoding="utf-8"))

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('system_date', ?)",
            [seed["system_date"]],
        )
        for table in [
            "plans",
            "customers",
            "subscriptions",
            "billing_records",
            "viewing_history",
            "support_tickets",
        ]:
            _insert_rows(conn, table, seed[table])
        conn.commit()
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    path = init_db()
    conn = sqlite3.connect(path)
    for (table,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name != 'sqlite_sequence'"
    ):
        (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        print(f"  {table:<16} {count:>3} 筆")
    conn.close()
    print(f"資料庫已建立：{path}")
