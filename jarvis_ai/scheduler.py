"""
Local task scheduler for recurring and one-off automations.
"""
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional

from jarvis_ai.config import Config

logger = logging.getLogger(__name__)


class Scheduler:
    """Persistent local scheduler backed by a JSON file."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = Path(storage_path or Config.SCHEDULE_FILE)
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def _load_tasks(self) -> List[Dict]:
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"Failed to load schedule: {exc}")
            return []

    def _save_tasks(self, tasks: List[Dict]):
        with self._lock:
            with open(self.storage_path, "w", encoding="utf-8") as handle:
                json.dump(tasks, handle, indent=2)

    def schedule_task(self, task_name: str, command: str, when: datetime, repeat: str = "once") -> str:
        tasks = self._load_tasks()
        task = {
            "id": str(uuid.uuid4()),
            "name": task_name,
            "command": command,
            "scheduled_time": when.isoformat(),
            "repeat": repeat,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        tasks.append(task)
        self._save_tasks(tasks)
        return f"✅ Scheduled: {task_name} at {when.strftime('%Y-%m-%d %H:%M')} ({repeat})"

    def list_tasks(self) -> str:
        tasks = [task for task in self._load_tasks() if task.get("status") == "pending"]
        if not tasks:
            return "No scheduled tasks"
        lines = ["📅 Scheduled Tasks:"]
        for task in tasks:
            lines.append(
                f"  • {task['name']} at {task['scheduled_time']} [{task['repeat']}] id={task['id'][:8]}"
            )
        return "\n".join(lines)

    def cancel_task(self, task_name: str) -> str:
        tasks = self._load_tasks()
        updated = False
        for task in tasks:
            if task.get("status") != "pending":
                continue
            if task.get("name") == task_name or task.get("id", "").startswith(task_name):
                task["status"] = "cancelled"
                task["cancelled_at"] = datetime.now().isoformat()
                updated = True
        if updated:
            self._save_tasks(tasks)
            return f"✅ Cancelled task: {task_name}"
        return "❌ Task not found"

    def start(self, executor_callback: Callable[[str], None]):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(
            target=self._run_scheduler,
            args=(executor_callback,),
            daemon=True,
        )
        self.thread.start()

    def stop(self):
        self.running = False

    def _run_scheduler(self, executor_callback: Callable[[str], None]):
        while self.running:
            now = datetime.now()
            tasks = self._load_tasks()
            dirty = False

            for task in tasks:
                if task.get("status") != "pending":
                    continue
                try:
                    scheduled_time = datetime.fromisoformat(task["scheduled_time"])
                except Exception:
                    task["status"] = "failed"
                    task["error"] = "Invalid scheduled time"
                    dirty = True
                    continue

                if now < scheduled_time:
                    continue

                try:
                    logger.info(f"Executing scheduled task: {task['name']}")
                    executor_callback(task["command"])
                    if task.get("repeat") == "once":
                        task["status"] = "completed"
                    else:
                        task["scheduled_time"] = self._calculate_next_time(
                            scheduled_time, task.get("repeat", "once")
                        ).isoformat()
                    task["executed_at"] = now.isoformat()
                except Exception as exc:
                    task["status"] = "failed"
                    task["error"] = str(exc)
                    logger.error(f"Task execution failed: {exc}")
                dirty = True

            if dirty:
                self._save_tasks(tasks)

            time.sleep(15)

    @staticmethod
    def _calculate_next_time(current: datetime, repeat: str) -> datetime:
        if repeat == "daily":
            return current + timedelta(days=1)
        if repeat == "weekly":
            return current + timedelta(weeks=1)
        if repeat == "monthly":
            return current + timedelta(days=30)
        return current
