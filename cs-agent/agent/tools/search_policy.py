"""內建工具 search_policy：在 knowledge/policies/ 裡搜尋相關的規則段落。

做法刻意保持簡單（不用向量資料庫）：
1. 把每份文件依「## 」標題切成段落，例如「P3-2 年繳退款」是一段。
2. 中文沒有空格分詞，所以把查詢切成「兩個字一組」（bigram），
   例如「退款期限」→ 退款、款期、期限，看每一段包含幾組。
3. 查詢裡直接寫段落編號（例如 P3-2）時，那一段一定排第一。

之後如果搜尋品質不夠，可以換成更好的方法，只要介面（query → 段落）不變，Agent 不用改。
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from agent import config

SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_policy",
        "description": (
            "搜尋星河影音的產品規則（方案說明、升降級、暫停、恢復、取消、退款、扣款失敗、轉接人工的條件）。"
            "回答任何產品規則問題、或判斷客戶的要求是否符合規則之前，都要先用本工具查詢。"
            "可以用關鍵字（例如「年繳 退款」）或段落編號（例如「P3-2」）查詢。"
            "注意：價格與方案規格不在這裡，請用 list_plans。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "要查的關鍵字或段落編號，例如「暫停 次數」或「P2-3」"},
            },
            "required": ["query"],
        },
    },
}

TOP_K = 3
SECTION_ID = re.compile(r"P\d+-\d+", re.IGNORECASE)


@dataclass
class Section:
    section_id: str   # P3-2
    title: str        # P3-2 年繳退款
    source: str       # 03_取消與退款.md
    text: str


@lru_cache(maxsize=1)
def _load_sections(folder: Path = config.KNOWLEDGE_DIR) -> list[Section]:
    sections = []
    for path in sorted(folder.glob("*.md")):
        # 用「## 」切段；第一塊是文件標題，不算段落
        for chunk in path.read_text(encoding="utf-8").split("\n## ")[1:]:
            title, _, body = chunk.partition("\n")
            match = SECTION_ID.match(title)
            sections.append(Section(
                section_id=match.group(0).upper() if match else title,
                title=title.strip(),
                source=path.name,
                text=body.strip(),
            ))
    return sections


def _terms(query: str) -> set[str]:
    """把查詢切成搜尋用的詞：英數字整個詞＋中文兩字一組。"""
    terms = {w.lower() for w in re.findall(r"[A-Za-z0-9_]+", query)}
    for run in re.findall(r"[一-鿿]+", query):
        if len(run) == 1:
            terms.add(run)
        terms.update(run[i:i + 2] for i in range(len(run) - 1))
    return terms


def _score(section: Section, terms: set[str]) -> int:
    title, text = section.title.lower(), section.text.lower()
    # 標題命中的權重較高
    return sum(3 * (t in title) + (t in text) for t in terms)


def run(query: str) -> dict:
    sections = _load_sections()
    wanted_ids = {m.upper() for m in SECTION_ID.findall(query)}
    terms = _terms(SECTION_ID.sub(" ", query))

    ranked = sorted(
        sections,
        key=lambda s: (s.section_id in wanted_ids, _score(s, terms)),
        reverse=True,
    )
    hits = [s for s in ranked if s.section_id in wanted_ids or _score(s, terms) > 0][:TOP_K]

    if not hits:
        return {"ok": True, "results": [], "message": "找不到相關規則，請換個關鍵字再查。"}
    return {
        "ok": True,
        "results": [{"section": s.title, "source": s.source, "text": s.text} for s in hits],
    }
