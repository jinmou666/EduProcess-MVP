import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "sql_app.db"

STAGE_KEYWORDS = {
    "research": ["资料检索", "破冰"],
    "framework": ["框架", "逻辑"],
    "content": ["内容生成", "开发"],
    "review": ["审阅", "纠错", "润色", "合规"],
}

TOOL_STAGE_PREFERENCE = {
    "Perplexity": ["research", "framework"],
    "Notion AI": ["framework", "content"],
    "GitHub Copilot": ["content", "review"],
    "Midjourney": ["content", "review"],
    "Claude 3.5": ["content", "review", "framework"],
    "ChatGPT": ["review", "content", "framework"],
}


def load_json(value):
    if value is None:
        return []
    if isinstance(value, str):
        return json.loads(value)
    return value


def detect_stage_type(stage_name):
    for stage_type, keywords in STAGE_KEYWORDS.items():
        if any(keyword in stage_name for keyword in keywords):
            return stage_type
    return "unknown"


def pick_stage_index(tool, stages):
    preferences = TOOL_STAGE_PREFERENCE.get(tool, [])
    indexed = list(enumerate(stages))

    for preferred_type in preferences:
        candidates = [
            (index, stage)
            for index, stage in indexed
            if stage.get("stage_type") == preferred_type and stage.get("aiPercent", 0) > 0
        ]
        if candidates:
            candidates.sort(key=lambda item: item[1].get("aiPercent", 0), reverse=True)
            return candidates[0][0]

    positive_ai_stages = [
        (index, stage) for index, stage in indexed if stage.get("aiPercent", 0) > 0
    ]
    if positive_ai_stages:
        positive_ai_stages.sort(key=lambda item: item[1].get("aiPercent", 0), reverse=True)
        return positive_ai_stages[0][0]

    return 0 if stages else None


def migrate():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "select id, collaboration_matrix, tools_used from authenticity_iterations order by id"
    ).fetchall()

    updated_count = 0

    for row_id, collaboration_matrix_raw, tools_used_raw in rows:
        collaboration_matrix = load_json(collaboration_matrix_raw)
        tools_used = load_json(tools_used_raw)

        if not collaboration_matrix:
            continue

        has_stage_tools = any("tools" in stage for stage in collaboration_matrix)
        if has_stage_tools:
            continue

        stages = []
        for stage in collaboration_matrix:
            stage_copy = dict(stage)
            stage_copy["stage_type"] = detect_stage_type(stage_copy.get("stageName", ""))
            stage_copy["tools"] = []
            stages.append(stage_copy)

        for tool in tools_used:
            target_index = pick_stage_index(tool, stages)
            if target_index is None:
                continue
            if tool not in stages[target_index]["tools"]:
                stages[target_index]["tools"].append(tool)

        cleaned_stages = []
        for stage in stages:
            stage.pop("stage_type", None)
            cleaned_stages.append(stage)

        conn.execute(
            "update authenticity_iterations set collaboration_matrix = ? where id = ?",
            (json.dumps(cleaned_stages, ensure_ascii=False), row_id),
        )
        updated_count += 1

    conn.commit()
    conn.close()
    print(f"Updated {updated_count} authenticity iteration records.")


if __name__ == "__main__":
    migrate()
