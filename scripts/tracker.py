import json
from datetime import datetime
from pathlib import Path


class LearningTracker:
    def __init__(self, project_root=None):
        if project_root is None:
            project_root = Path.cwd()
        self.project_root = Path(project_root)
        self.learning_dir = self.project_root / ".learning"
        self.checkins_dir = self.learning_dir / "checkins"
        self.reports_dir = self.learning_dir / "reports"
        self.learning_dir.mkdir(exist_ok=True)
        self.checkins_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)

    def init_plan(self, goal, start_date, end_date, daily_hours):
        plan = {"goal": goal, "start_date": start_date, "end_date": end_date, "daily_hours": daily_hours}
        with open(self.learning_dir / "plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        progress = {"created_at": start_date, "last_checkin": None, "total_hours": 0, "streak": 0, "tasks": []}
        with open(self.learning_dir / "progress.json", "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        return plan

    def add_task(self, name, estimated_hours):
        pf = self.learning_dir / "progress.json"
        with open(pf, "r", encoding="utf-8") as f:
            progress = json.load(f)
        task_id = f"task-{len(progress['tasks']) + 1}"
        task = {"id": task_id, "name": name, "status": "pending", "progress": 0, "estimated_hours": estimated_hours, "actual_hours": 0}
        progress["tasks"].append(task)
        with open(pf, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        return task

    def checkin(self, task_id, content, duration_minutes, completed=False):
        today = datetime.now().strftime("%Y-%m-%d")
        cf = self.checkins_dir / f"{today}.json"
        if cf.exists():
            with open(cf, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"date": today, "tasks": [], "total_minutes": 0}
        rec = {"task_id": task_id, "content": content, "duration_minutes": duration_minutes, "completed": completed, "timestamp": datetime.now().isoformat()}
        data["tasks"].append(rec)
        data["total_minutes"] += duration_minutes
        with open(cf, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._update_progress(task_id, duration_minutes, completed)
        return data

    def _update_progress(self, task_id, duration_minutes, completed):
        pf = self.learning_dir / "progress.json"
        with open(pf, "r", encoding="utf-8") as f:
            progress = json.load(f)
        progress["total_hours"] += duration_minutes / 60
        progress["last_checkin"] = datetime.now().strftime("%Y-%m-%d")
        for task in progress["tasks"]:
            if task["id"] == task_id:
                task["actual_hours"] += duration_minutes / 60
                if completed:
                    task["status"] = "completed"
                    task["progress"] = 100
                elif task["status"] == "pending":
                    task["status"] = "in_progress"
                break
        with open(pf, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def get_progress(self):
        pf = self.learning_dir / "progress.json"
        if not pf.exists():
            return None
        with open(pf, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_report(self):
        progress = self.get_progress()
        if not progress:
            return "No data"
        total = len(progress["tasks"])
        done = sum(1 for t in progress["tasks"] if t["status"] == "completed")
        lines = ["# Learning Report", "", "## Stats", f"- Total: {progress['total_hours']:.1f}h", f"- Tasks: {done}/{total}", "", "## Tasks"]
        for t in progress["tasks"]:
            icon = "DONE" if t["status"] == "completed" else "WIP" if t["status"] == "in_progress" else "TODO"
            lines.append(f"- [{icon}] {t['name']} ({t['progress']}%)")
        return "\n".join(lines)


if __name__ == "__main__":
    tracker = LearningTracker()
    print(tracker.generate_report())
