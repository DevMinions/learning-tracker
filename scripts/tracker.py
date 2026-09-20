#!/usr/bin/env python3
"""学习追踪：计划 + 打卡 + 间隔复习。

统计量全部从打卡记录推导，不落盘。任务用「完成标准」定义，不用小时数定义。

    tracker.py init "目标" 2026-09-20 2027-09-20 3.5
    tracker.py add "线代直觉" 8 --dod "不查资料说出 Linear 的输出 shape"
    tracker.py dod task-1 "..."                      # 补/改完成标准
    tracker.py checkin task-1 "看了3B1B第3集" 45 [--done] [--notes "..."]
    tracker.py ask task-1 "为什么 Linear 只作用在最后一维" "因为它是..."
    tracker.py quiz [--limit 5]                      # 到期的题，只出题不给答案
    tracker.py answer q-1                            # 看标准答案（判卷用）
    tracker.py grade q-1 ok|fail                     # 答对进一级，答错回第一级
    tracker.py report
    tracker.py selftest
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ponytail: 固定阶梯，不是 SM-2。等到每天几十道题、且这个阶梯明显不合身再换。
LADDER = [1, 3, 7, 21, 60]


class LearningTracker:
    def __init__(self, project_root=None):
        self.dir = Path(project_root or Path.cwd()) / ".learning"
        self.plan_file = self.dir / "plan.json"
        self.reviews_file = self.dir / "reviews.json"
        self.checkins_dir = self.dir / "checkins"

    def _write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_plan(self):
        if not self.plan_file.exists():
            raise FileNotFoundError(f"还没有学习计划，先运行 init（预期 {self.plan_file}）")
        return json.loads(self.plan_file.read_text(encoding="utf-8"))

    def _task(self, plan, task_id):
        task = next((t for t in plan["tasks"] if t["id"] == task_id), None)
        if task is None:
            raise KeyError(f"没有任务 {task_id}，现有：{[t['id'] for t in plan['tasks']] or '（空）'}")
        return task

    # ---------- 计划 ----------

    def init_plan(self, goal, start_date, end_date, daily_hours):
        for d in (start_date, end_date):
            datetime.strptime(d, "%Y-%m-%d")  # 早失败好过写坏数据
        plan = {"goal": goal, "start_date": start_date, "end_date": end_date,
                "daily_hours": daily_hours, "tasks": []}
        self._write(self.plan_file, plan)
        return plan

    def add_task(self, name, estimated_hours, dod=""):
        plan = self.load_plan()
        task = {"id": f"task-{len(plan['tasks']) + 1}", "name": name,
                "estimated_hours": estimated_hours, "dod": dod, "done": False}
        plan["tasks"].append(task)
        self._write(self.plan_file, plan)
        return task

    def set_dod(self, task_id, dod):
        plan = self.load_plan()
        task = self._task(plan, task_id)
        task["dod"] = dod
        self._write(self.plan_file, plan)
        return task

    # ---------- 打卡 ----------

    def checkin(self, task_id, content, duration_minutes, completed=False, notes="", today=None):
        if duration_minutes <= 0:
            raise ValueError("时长必须为正数")
        plan = self.load_plan()
        task = self._task(plan, task_id)
        today = today or date.today().isoformat()
        cf = self.checkins_dir / f"{today}.json"
        data = json.loads(cf.read_text(encoding="utf-8")) if cf.exists() else {"date": today, "tasks": []}
        data["tasks"].append({"task_id": task_id, "content": content,
                              "duration_minutes": duration_minutes, "completed": completed,
                              "notes": notes, "timestamp": datetime.now().isoformat(timespec="seconds")})
        self._write(cf, data)
        if completed and not task["done"]:
            task["done"] = True
            self._write(self.plan_file, plan)
        return data

    def checkins(self):
        out = []
        for f in sorted(self.checkins_dir.glob("[0-9]*.json")):
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                print(f"跳过损坏的打卡文件 {f}", file=sys.stderr)
        return out

    # ---------- 复习 ----------

    def _reviews(self):
        if not self.reviews_file.exists():
            return {"items": []}
        return json.loads(self.reviews_file.read_text(encoding="utf-8"))

    def ask(self, task_id, q, a, today=None):
        """存一道题。学完当天不考，第一次复习安排在明天。"""
        self._task(self.load_plan(), task_id)  # 校验任务存在
        rv = self._reviews()
        today = date.fromisoformat(today) if today else date.today()
        item = {"id": f"q-{len(rv['items']) + 1}", "task_id": task_id, "q": q, "a": a,
                "level": 0, "due": (today + timedelta(days=LADDER[0])).isoformat(), "fails": 0}
        rv["items"].append(item)
        self._write(self.reviews_file, rv)
        return item

    def due_items(self, today=None, limit=None):
        today = today or date.today().isoformat()
        due = [i for i in self._reviews()["items"] if i["due"] <= today]
        due.sort(key=lambda i: (-i["fails"], i["due"]))  # 反复答错的先问
        return due[:limit] if limit else due

    def grade(self, item_id, ok, today=None):
        rv = self._reviews()
        item = next((i for i in rv["items"] if i["id"] == item_id), None)
        if item is None:
            raise KeyError(f"没有题目 {item_id}")
        today = date.fromisoformat(today) if today else date.today()
        if ok:
            item["level"] = min(item["level"] + 1, len(LADDER) - 1)
        else:
            item["level"] = 0
            item["fails"] += 1
        item["due"] = (today + timedelta(days=LADDER[item["level"]])).isoformat()
        self._write(self.reviews_file, rv)
        return item

    def get_item(self, item_id):
        item = next((i for i in self._reviews()["items"] if i["id"] == item_id), None)
        if item is None:
            raise KeyError(f"没有题目 {item_id}")
        return item

    # ---------- 统计 ----------

    def stats(self, today=None):
        """全部从 checkins/ 和 reviews.json 推导——没有可能与记录不一致的第二份真相。"""
        days = self.checkins()
        minutes = {}
        for d in days:
            for t in d["tasks"]:
                minutes[t["task_id"]] = minutes.get(t["task_id"], 0) + t["duration_minutes"]
        dates = {d["date"] for d in days if d["tasks"]}
        today_d = date.fromisoformat(today) if today else date.today()
        # 今天还没打卡不该把连胜清零，所以从今天或昨天起往回数
        cursor = today_d if today_d.isoformat() in dates else today_d - timedelta(days=1)
        streak = 0
        while cursor.isoformat() in dates:
            streak += 1
            cursor -= timedelta(days=1)
        items = self._reviews()["items"]
        return {"total_hours": sum(minutes.values()) / 60, "streak": streak,
                "last_checkin": max(dates) if dates else None,
                "task_hours": {k: v / 60 for k, v in minutes.items()},
                "due": len(self.due_items(today)), "items": len(items),
                "mastered": sum(1 for i in items if i["level"] >= 3),
                "shaky": [i for i in items if i["fails"] >= 2]}

    def report(self, today=None):
        plan = self.load_plan()
        s = self.stats(today)
        tasks = plan["tasks"]
        done = sum(1 for t in tasks if t["done"])
        lines = [f"# 学习进度报告：{plan['goal']}", ""]
        if s["due"]:
            lines.append(f"**⚠️ {s['due']} 道题到期待复习 —— 先 quiz，再学新的。**")
            lines.append("")
        lines += [f"- 掌握：{s['mastered']}/{s['items']} 题（答对 3 次以上算掌握）",
                  f"- 完成任务：{done}/{len(tasks)}",
                  f"- 总学习时间：{s['total_hours']:.1f} 小时",
                  f"- 连续打卡：{s['streak']} 天（最近 {s['last_checkin'] or '还没有'}）",
                  f"- 时间范围：{plan['start_date']} → {plan['end_date']}（每日 {plan['daily_hours']}h）",
                  "", "## 任务"]
        for t in tasks:
            h = s["task_hours"].get(t["id"], 0)
            est = t["estimated_hours"]
            pct = 100 if t["done"] else min(99, round(h / est * 100)) if est else 0
            lines.append(f"- [{'✅' if t['done'] else '⏳' if h else '⬜'}] {t['id']} {t['name']}"
                         f" — {h:.1f}/{est}h ({pct}%)")
            if t.get("dod"):
                lines.append(f"      完成标准：{t['dod']}")
        if s["shaky"]:
            lines += ["", "## 反复答错（这些才是真缺口）"]
            for i in s["shaky"]:
                lines.append(f"- {i['id']} 错 {i['fails']} 次：{i['q']}")
        return "\n".join(lines)


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        t = LearningTracker(tmp)
        for exc, fn in [(FileNotFoundError, lambda: t.add_task("x", 1))]:
            try:
                fn(); assert False, "无计划时应报错"
            except exc:
                pass
        t.init_plan("成为算法工程师", "2026-09-01", "2026-12-01", 2)
        t.add_task("线性代数", 10, dod="能手推矩阵乘法的 shape")
        assert "能手推矩阵乘法的 shape" in t.report(today="2026-09-18")
        t.set_dod("task-1", "改过的标准")
        assert t.load_plan()["tasks"][0]["dod"] == "改过的标准"
        for exc, fn in [(KeyError, lambda: t.checkin("task-999", "错id", 60)),
                        (ValueError, lambda: t.checkin("task-1", "负时长", -5)),
                        (KeyError, lambda: t.ask("task-9", "q", "a")),
                        (KeyError, lambda: t.grade("q-99", True))]:
            try:
                fn(); assert False, f"应抛 {exc.__name__}"
            except exc:
                pass
        # 打卡与连胜
        t.checkin("task-1", "第1天", 30, today="2026-09-18")
        t.checkin("task-1", "第2天", 45, today="2026-09-19")
        t.checkin("task-1", "第3天", 45, today="2026-09-20")
        s = t.stats(today="2026-09-20")
        assert s["streak"] == 3 and abs(s["total_hours"] - 2.0) < 1e-9, s
        assert t.stats(today="2026-09-21")["streak"] == 3, "今天没打卡不清零"
        assert t.stats(today="2026-09-22")["streak"] == 0, "断一天要清零"
        # 复习阶梯
        t.ask("task-1", "为什么除以 sqrt(d_k)", "防止点积方差过大导致 softmax 饱和", today="2026-09-20")
        assert t.due_items(today="2026-09-20") == [], "当天学完不该当天考"
        assert len(t.due_items(today="2026-09-21")) == 1, "隔天该到期"
        assert t.get_item("q-1")["a"].startswith("防止")
        t.grade("q-1", True, today="2026-09-21")          # level 0 -> 1, +3d
        assert t.get_item("q-1")["due"] == "2026-09-24"
        assert t.due_items(today="2026-09-23") == [], "没到期不该出现"
        t.grade("q-1", False, today="2026-09-24")         # 答错回第一级
        it = t.get_item("q-1")
        assert it["level"] == 0 and it["fails"] == 1 and it["due"] == "2026-09-25", it
        for d in ["2026-09-25", "2026-09-26", "2026-09-29", "2026-10-06"]:
            t.grade("q-1", True, today=d)
        assert t.get_item("q-1")["level"] == 4, "阶梯封顶在最后一级"
        assert t.stats(today="2026-10-06")["mastered"] == 1
        # 反复答错要在报告里点名
        t.ask("task-1", "causal mask 忘了加 loss 会怎样", "异常地低", today="2026-09-20")
        t.grade("q-2", False, today="2026-09-21"); t.grade("q-2", False, today="2026-09-22")
        r = t.report(today="2026-09-23")
        assert "反复答错" in r and "q-2 错 2 次" in r and "道题到期待复习" in r, r
        # 完成标准 + 完成态
        t.checkin("task-1", "收工", 10, completed=True, today="2026-09-20")
        assert t.load_plan()["tasks"][0]["done"] and "(100%)" in t.report(today="2026-09-20")
    print("selftest OK")


def main():
    p = argparse.ArgumentParser(description="学习计划、打卡与间隔复习")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="创建学习计划")
    i.add_argument("goal"); i.add_argument("start_date"); i.add_argument("end_date")
    i.add_argument("daily_hours", type=float)
    a = sub.add_parser("add", help="添加任务")
    a.add_argument("name"); a.add_argument("estimated_hours", type=float)
    a.add_argument("--dod", default="", help="完成标准：能做出什么才算完成")
    d = sub.add_parser("dod", help="补/改任务的完成标准")
    d.add_argument("task_id"); d.add_argument("text")
    c = sub.add_parser("checkin", help="记录一次学习")
    c.add_argument("task_id"); c.add_argument("content"); c.add_argument("minutes", type=int)
    c.add_argument("--done", action="store_true"); c.add_argument("--notes", default="")
    k = sub.add_parser("ask", help="存一道复习题")
    k.add_argument("task_id"); k.add_argument("q"); k.add_argument("a")
    q = sub.add_parser("quiz", help="列出到期的题（不含答案）")
    q.add_argument("--limit", type=int, default=5)
    an = sub.add_parser("answer", help="查看某题的标准答案（判卷用）")
    an.add_argument("item_id")
    g = sub.add_parser("grade", help="判卷")
    g.add_argument("item_id"); g.add_argument("result", choices=["ok", "fail"])
    sub.add_parser("report", help="生成进度报告")
    sub.add_parser("selftest", help="自检")
    args = p.parse_args()

    t = LearningTracker()
    try:
        if args.cmd == "init":
            print(json.dumps(t.init_plan(args.goal, args.start_date, args.end_date, args.daily_hours),
                             ensure_ascii=False, indent=2))
        elif args.cmd == "add":
            print(json.dumps(t.add_task(args.name, args.estimated_hours, args.dod), ensure_ascii=False))
        elif args.cmd == "dod":
            print(json.dumps(t.set_dod(args.task_id, args.text), ensure_ascii=False))
        elif args.cmd == "checkin":
            t.checkin(args.task_id, args.content, args.minutes, args.done, args.notes)
            print(t.report())
        elif args.cmd == "ask":
            print(json.dumps(t.ask(args.task_id, args.q, args.a), ensure_ascii=False))
        elif args.cmd == "quiz":
            due = t.due_items(limit=args.limit)
            if not due:
                print("没有到期的题。")
            for it in due:
                flag = f"（曾错 {it['fails']} 次）" if it["fails"] else ""
                print(f"{it['id']} [{it['task_id']}]{flag} {it['q']}")
        elif args.cmd == "answer":
            print(t.get_item(args.item_id)["a"])
        elif args.cmd == "grade":
            it = t.grade(args.item_id, args.result == "ok")
            print(f"{it['id']} → level {it['level']}，下次复习 {it['due']}"
                  + (f"，累计答错 {it['fails']} 次" if it["fails"] else ""))
        elif args.cmd == "report":
            print(t.report())
        elif args.cmd == "selftest":
            selftest()
    except (FileNotFoundError, KeyError, ValueError) as e:
        sys.exit(f"错误：{e}")


if __name__ == "__main__":
    main()
