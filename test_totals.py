"""Тесты учёта общего затраченного времени.

Запуск: python -m unittest test_totals -v
"""
import unittest
from datetime import timedelta

from task_system_time_tracking import (
    NoActiveTimerError, NotAssignedError, PenaltyPolicy, PenaltyReason,
    Priority, Status, TaskClosedError, TimedTaskManager,
    TimerAlreadyRunningError, UnknownTaskError, UnknownUserError,
    format_duration)
from tt_helpers import TimeTrackingTestCase


class TestTotals(TimeTrackingTestCase):
    def test_total_accumulates_sessions(self):
        self.work(self.anna, self.t1, hours=1)
        self.clock.advance(hours=2)                      # перерыв не считается
        self.work(self.anna, self.t1, minutes=30)
        self.assertEqual(self.m.tracker.total_time(self.t1.task_id),
                         timedelta(hours=1, minutes=30))

    def test_running_timer_included_optionally(self):
        self.m.start_timer(self.anna.user_id, self.t1.task_id)
        self.clock.advance(minutes=20)
        tr = self.m.tracker
        self.assertEqual(tr.total_time(self.t1.task_id), timedelta(minutes=20))
        self.assertEqual(tr.total_time(self.t1.task_id, include_running=False),
                         timedelta())
        self.assertEqual(tr.user_time(self.anna.user_id), timedelta(minutes=20))
        self.assertEqual(tr.user_time(self.anna.user_id, False), timedelta())

    def test_user_time_over_tasks(self):
        self.work(self.anna, self.t1, hours=1)
        self.work(self.anna, self.t2, hours=2)
        self.assertEqual(self.m.tracker.user_time(self.anna.user_id),
                         timedelta(hours=3))

    def test_entries_filters(self):
        self.work(self.anna, self.t1, hours=1)
        self.work(self.anna, self.t2, hours=1)
        tr = self.m.tracker
        self.assertEqual(len(tr.entries()), 2)
        self.assertEqual(len(tr.entries(task_id=self.t1.task_id)), 1)
        self.assertEqual(len(tr.entries(user_id=self.boris.user_id)), 0)

    def test_total_unknown_ids(self):
        with self.assertRaises(UnknownTaskError):
            self.m.tracker.total_time(99)
        with self.assertRaises(UnknownUserError):
            self.m.tracker.user_time(99)

    def test_duration_of_running_entry_needs_now(self):
        e = self.m.start_timer(self.anna.user_id, self.t1.task_id)
        with self.assertRaises(ValueError):
            e.duration()


if __name__ == "__main__":
    unittest.main()
