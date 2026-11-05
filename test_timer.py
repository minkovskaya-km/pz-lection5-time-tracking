"""Тесты таймера: старт, остановка, ограничения.

Запуск: python -m unittest test_timer -v
"""
import unittest
from datetime import timedelta

from task_system_time_tracking import (
    NoActiveTimerError, NotAssignedError, PenaltyPolicy, PenaltyReason,
    Priority, Status, TaskClosedError, TimedTaskManager,
    TimerAlreadyRunningError, UnknownTaskError, UnknownUserError,
    format_duration)
from tt_helpers import TimeTrackingTestCase


class TestTimer(TimeTrackingTestCase):
    def test_start_stop_measures_duration(self):
        entry = self.work(self.anna, self.t1, hours=1, minutes=30)
        self.assertEqual(entry.duration(), timedelta(hours=1, minutes=30))
        self.assertFalse(entry.is_running)
        self.assertIsNone(self.m.tracker.active_timer(self.anna.user_id))

    def test_start_sets_in_progress(self):
        self.t1.update_status(Status.TODO)
        self.m.start_timer(self.anna.user_id, self.t1.task_id)
        self.assertEqual(self.t1.status, Status.IN_PROGRESS)

    def test_active_timer_visible(self):
        e = self.m.start_timer(self.anna.user_id, self.t1.task_id)
        self.assertIs(self.m.tracker.active_timer(self.anna.user_id), e)
        self.assertTrue(e.is_running)

    def test_second_timer_for_same_user_rejected(self):
        self.m.start_timer(self.anna.user_id, self.t1.task_id)
        with self.assertRaises(TimerAlreadyRunningError):
            self.m.start_timer(self.anna.user_id, self.t2.task_id)

    def test_stop_without_timer_rejected(self):
        with self.assertRaises(NoActiveTimerError):
            self.m.stop_timer(self.anna.user_id)

    def test_unknown_user_and_task(self):
        with self.assertRaises(UnknownUserError):
            self.m.start_timer(99, self.t1.task_id)
        with self.assertRaises(UnknownTaskError):
            self.m.start_timer(self.anna.user_id, 99)
        with self.assertRaises(UnknownUserError):
            self.m.stop_timer(99)

    def test_not_assigned_rejected(self):
        with self.assertRaises(NotAssignedError):
            self.m.start_timer(self.boris.user_id, self.t1.task_id)
        unassigned = self.m.create_task("Без исполнителя", "d", Priority.LOW, self.due)
        with self.assertRaises(NotAssignedError):
            self.m.start_timer(self.anna.user_id, unassigned.task_id)

    def test_done_task_rejected(self):
        self.m.complete_task(self.t1.task_id)
        with self.assertRaises(TaskClosedError):
            self.m.start_timer(self.anna.user_id, self.t1.task_id)


if __name__ == "__main__":
    unittest.main()
