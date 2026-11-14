"""內建工具 load_skill：載入一份 Skill 的完整處理步驟。

漸進式揭露（書上第二章「Skills 在上下文中的位置」）：
- 啟動時：catalog() 只把每個 Skill 的 name + description 放進系統提示詞。
- 需要時：模型呼叫 load_skill(name)，SKILL.md 全文才以「工具結果」的形式加到對話最後面。
  這是書上說的「沒有專用啟用機制的 Harness 用工具讀取」的做法；
  因為是加在最後面，前面的系統提示詞不變，KV Cache 不會失效。

安全：name 只能是目錄裡有的名字。
如果直接拿 name 去拼檔案路徑，模型（或注入攻擊）傳進 "../../.env" 就能讀到密鑰。
"""

from functools import lru_cache
from pathlib import Path

from agent import config

SCHEMA = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": "載入某個處理流程（Skill）的完整步驟。開始處理系統提示詞「Skills 目錄」列出的任務之前，先用本工具載入對應的流程，再照著步驟做。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill 名稱，必須是 Skills 目錄裡的其中一個，例如 cancel-and-refund"},
            },
            "required": ["name"],
        },
    },
}


def _parse(path: Path) -> tuple[dict, str]:
    """拆開 SKILL.md 的 frontmatter（--- 之間的 name / description）與正文。"""
    text = path.read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    meta = {}
    for line in front.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body.strip()


@lru_cache(maxsize=1)
def _skills(folder: Path = config.SKILLS_DIR) -> dict[str, dict]:
    skills = {}
    for path in sorted(folder.glob("*/SKILL.md")):
        meta, body = _parse(path)
        skills[meta["name"]] = {"description": meta["description"], "body": body}
    return skills


def catalog() -> str:
    """給系統提示詞用的 Skills 目錄（只有 name 和 description）。"""
    return "\n".join(f"- `{name}`：{s['description']}" for name, s in _skills().items())


def run(name: str) -> dict:
    skills = _skills()
    if name not in skills:
        return {"ok": False, "error": f"沒有名為 {name!r} 的 Skill。可用的有：{', '.join(skills)}"}
    return {"ok": True, "skill": name, "instructions": skills[name]["body"]}
