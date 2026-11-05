"""Тесты отчётов по времени.

Запуск: python -m unittest test_reports -v
"""
import unittest
from datetime import timedelta

from task_system_time_tracking import (
    NoActiveTimerError, NotAssignedError, PenaltyPolicy, PenaltyReason,
    Priority, Status, TaskClosedError, TimedTaskManager,
    TimerAlreadyRunningError, UnknownTaskError, UnknownUserError,
    format_duration)
from tt_helpers import TimeTrackingTestCase


class TestReports(TimeTrackingTestCase):
    def test_report_structure_and_totals(self):
        self.work(self.anna, self.t1, hours=1)
        self.m.assign_task(self.t2.task_id, self.boris.user_id)
        self.work(self.boris, self.t2, hours=2, minutes=30)
        r = self.m.tracker.generate_time_report()
        self.assertEqual(r["total_time"], "3:30:00")
        self.assertEqual(r["sessions"], 2)
        self.assertEqual(r["by_task"][0],
                         {"task_id": 1, "title": "Задача 1", "time": "1:00:00"})
        self.assertEqual([u["name"] for u in r["by_user"]], ["Анна", "Борис"])

    def test_report_period_filter(self):
        self.work(self.anna, self.t1, hours=1)
        cut = self.clock.now
        self.clock.advance(days=1)
        self.work(self.anna, self.t1, hours=2)
        later = self.m.tracker.generate_time_report(date_from=cut)
        self.assertEqual(later["total_time"], "2:00:00")
        earlier = self.m.tracker.generate_time_report(date_to=cut)
        self.assertEqual(earlier["total_time"], "1:00:00")

    def test_report_counts_running_timer(self):
        self.m.start_timer(self.anna.user_id, self.t1.task_id)
        self.clock.advance(minutes=45)
        r = self.m.tracker.generate_time_report()
        self.assertEqual(r["running_timers"], 1)
        self.assertEqual(r["total_time"], "0:45:00")

    def test_report_contains_penalties(self):
        self.clock.advance(days=4)
        self.m.complete_task(self.t1.task_id)
        r = self.m.tracker.generate_time_report()
        self.assertEqual(r["penalties"][0]["points"], 15)

    def test_text_report(self):
        self.work(self.anna, self.t1, hours=1)
        text = self.m.time_report_text()
        self.assertIn("ОТЧЁТ ПО ВРЕМЕНИ", text)
        self.assertIn("Анна: 1:00:00, штрафы: 0", text)
        self.assertIn("нет", text)

    def test_text_report_with_penalty(self):
        self.clock.advance(days=4)
        self.m.complete_task(self.t1.task_id)
        self.assertIn("Задача закрыта после срока (+15)", self.m.time_report_text())

    def test_text_report_empty(self):
        text = self.m.time_report_text()
        self.assertIn("Всего: 0:00:00", text)

    def test_integration_with_task_report(self):
        self.work(self.anna, self.t1, hours=1)
        r = self.m.generate_report()
        self.assertEqual(r["total_tasks"], 2)           # отчёт из лекции
        self.assertEqual(r["time"]["total_time"], "1:00:00")

    def test_format_duration(self):
        self.assertEqual(format_duration(timedelta(hours=26, minutes=5, seconds=7)),
                         "26:05:07")
        self.assertEqual(format_duration(timedelta(seconds=-61)), "-0:01:01")


if __name__ == "__main__":
    unittest.main()
