#!/usr/bin/env python3
"""把 .learning/ 的数据烤进一个自包含 HTML，交给 Artifact 发布。

    python3 scripts/dashboard.py [输出路径]

只读快照：真数据源始终是本地 .learning/，页面不回写。想看最新的就重跑这条命令再发布一次。
"""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from tracker import LearningTracker

TEMPLATE = Path(__file__).with_name("dashboard.html")


def build(root=None, days=14):
    t = LearningTracker(root)
    plan = t.load_plan()
    s = t.stats()
    by_day = {d["date"]: sum(x["duration_minutes"] for x in d["tasks"]) for d in t.checkins()}
    today = date.today()

    tasks = []
    for task in plan["tasks"]:
        h = s["task_hours"].get(task["id"], 0)
        est = task["estimated_hours"]
        tasks.append({**task, "hours": h,
                      "pct": 100 if task["done"] else (min(99, round(h / est * 100)) if est else 0)})
    nxt = next((x for x in tasks if not x["done"]), None)

    data = {
        "goal": plan["goal"], "start_date": plan["start_date"], "end_date": plan["end_date"],
        "daily_hours": plan["daily_hours"], "note": plan.get("note", ""),
        "phases": plan.get("phases", []), "current_phase": plan.get("current_phase", ""),
        "tasks": tasks, "next": nxt, "stats": s,
        "daily": [{"date": (d := (today - timedelta(days=i)).isoformat()), "minutes": by_day.get(d, 0)}
                  for i in range(days - 1, -1, -1)],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    html = TEMPLATE.read_text(encoding="utf-8")
    return (html.replace("__TITLE__", plan.get("title") or plan["goal"])
                .replace("__DATA__", json.dumps(data, ensure_ascii=False)))


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "dashboard.html")
    out.write_text(build(), encoding="utf-8")
    print(out.resolve())
