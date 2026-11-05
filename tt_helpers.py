"""Общие помощники для тестов: управляемые часы и базовый тестовый класс."""
import unittest
from datetime import datetime, timedelta
from typing import Optional

from task_system_time_tracking import Priority, TimedTaskManager


class FakeClock:
    """Управляемые часы для тестов."""

    def __init__(self, now: Optional[datetime] = None):
        self.now = now or datetime(2026, 1, 12, 9, 0, 0)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


class TimeTrackingTestCase(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.m = TimedTaskManager(clock=self.clock)
        self.anna = self.m.create_user("Анна", "anna@company.com")
        self.boris = self.m.create_user("Борис", "boris@company.com")
        self.due = self.clock.now + timedelta(days=3)
        self.t1 = self.m.create_task("Задача 1", "d", Priority.HIGH, self.due)
        self.t2 = self.m.create_task("Задача 2", "d", Priority.LOW, self.due)
        self.m.assign_task(self.t1.task_id, self.anna.user_id)
        self.m.assign_task(self.t2.task_id, self.anna.user_id)

    def work(self, user, task, **dur):
        self.m.start_timer(user.user_id, task.task_id)
        self.clock.advance(**dur)
        return self.m.stop_timer(user.user_id)
