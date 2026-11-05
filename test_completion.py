"""Тесты завершения задачи (интеграция таймера и задач).

Запуск: python -m unittest test_completion -v
"""
import unittest
from datetime import timedelta

from task_system_time_tracking import (
    NoActiveTimerError, NotAssignedError, PenaltyPolicy, PenaltyReason,
    Priority, Status, TaskClosedError, TimedTaskManager,
    TimerAlreadyRunningError, UnknownTaskError, UnknownUserError,
    format_duration)
from tt_helpers import TimeTrackingTestCase


class TestCompletion(TimeTrackingTestCase):
    def test_complete_stops_running_timer(self):
        self.m.start_timer(self.anna.user_id, self.t1.task_id)
        self.clock.advance(hours=1)
        self.m.complete_task(self.t1.task_id)
        self.assertIsNone(self.m.tracker.active_timer(self.anna.user_id))
        self.assertEqual(self.m.tracker.total_time(self.t1.task_id), timedelta(hours=1))

    def test_complete_twice_rejected(self):
        self.m.complete_task(self.t1.task_id)
        with self.assertRaises(TaskClosedError):
            self.m.complete_task(self.t1.task_id)

    def test_complete_unknown_task(self):
        with self.assertRaises(UnknownTaskError):
            self.m.complete_task(99)

    def test_complete_keeps_other_users_timer(self):
        self.m.assign_task(self.t2.task_id, self.boris.user_id)
        self.m.start_timer(self.boris.user_id, self.t2.task_id)
        self.m.complete_task(self.t1.task_id)
        self.assertIsNotNone(self.m.tracker.active_timer(self.boris.user_id))


if __name__ == "__main__":
    unittest.main()
