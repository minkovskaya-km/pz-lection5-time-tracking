"""Тесты системы штрафов.

Запуск: python -m unittest test_penalties -v
"""
import unittest
from datetime import timedelta

from task_system_time_tracking import (
    NoActiveTimerError, NotAssignedError, PenaltyPolicy, PenaltyReason,
    Priority, Status, TaskClosedError, TimedTaskManager,
    TimerAlreadyRunningError, UnknownTaskError, UnknownUserError,
    format_duration)
from tt_helpers import TimeTrackingTestCase


class TestPenalties(TimeTrackingTestCase):
    def test_on_time_completion_no_penalty(self):
        self.work(self.anna, self.t1, hours=1)
        self.assertEqual(self.m.complete_task(self.t1.task_id), [])
        self.assertEqual(self.m.user_penalty(self.anna.user_id), 0)
        self.assertEqual(self.t1.status, Status.DONE)

    def test_late_completion_penalty_by_days(self):
        self.clock.advance(days=5, hours=3)              # срок + 2 дня 3 часа
        penalties = self.m.complete_task(self.t1.task_id)
        self.assertEqual(len(penalties), 1)
        self.assertEqual(penalties[0].reason, PenaltyReason.LATE_COMPLETION)
        self.assertEqual(penalties[0].points, 10 + 5 * 2)
        self.assertEqual(self.m.user_penalty(self.anna.user_id), 20)

    def test_late_same_day_only_base(self):
        self.clock.advance(days=3, hours=1)
        self.assertEqual(self.m.complete_task(self.t1.task_id)[0].points, 10)

    def test_forgotten_timer_cut_on_stop(self):
        self.m.start_timer(self.anna.user_id, self.t1.task_id)
        self.clock.advance(hours=20)
        entry = self.m.stop_timer(self.anna.user_id)
        self.assertTrue(entry.auto_stopped)
        self.assertEqual(entry.duration(), timedelta(hours=8))
        self.assertEqual(self.m.user_penalty(self.anna.user_id), 5)

    def test_session_at_limit_is_not_forgotten(self):
        entry = self.work(self.anna, self.t1, hours=8)
        self.assertFalse(entry.auto_stopped)
        self.assertEqual(self.m.user_penalty(self.anna.user_id), 0)

    def test_sweep_stops_forgotten_timers(self):
        self.m.start_timer(self.anna.user_id, self.t1.task_id)
        self.clock.advance(hours=9)
        stopped = self.m.tracker.check_forgotten_timers()
        self.assertEqual(len(stopped), 1)
        self.assertIsNone(self.m.tracker.active_timer(self.anna.user_id))
        self.assertEqual(self.m.tracker.check_forgotten_timers(), [])

    def test_forgotten_timer_does_not_block_new_start(self):
        self.m.start_timer(self.anna.user_id, self.t1.task_id)
        self.clock.advance(hours=12)
        self.m.start_timer(self.anna.user_id, self.t2.task_id)   # без ошибки
        self.assertEqual(self.m.user_penalty(self.anna.user_id), 5)

    def test_over_estimate_penalty(self):
        self.m.tracker.set_estimate(self.t1.task_id, timedelta(hours=2))
        self.work(self.anna, self.t1, hours=3)           # > 2.4 ч
        penalties = self.m.complete_task(self.t1.task_id)
        self.assertEqual([p.reason for p in penalties], [PenaltyReason.OVER_ESTIMATE])
        self.assertEqual(penalties[0].points, 3)

    def test_within_tolerance_no_penalty(self):
        self.m.tracker.set_estimate(self.t1.task_id, timedelta(hours=2))
        self.work(self.anna, self.t1, hours=2, minutes=20)   # < 2.4 ч
        self.assertEqual(self.m.complete_task(self.t1.task_id), [])

    def test_no_estimate_no_over_estimate_penalty(self):
        self.work(self.anna, self.t1, hours=7)
        self.assertEqual(self.m.complete_task(self.t1.task_id), [])

    def test_penalties_stack(self):
        self.m.tracker.set_estimate(self.t1.task_id, timedelta(hours=1))
        self.work(self.anna, self.t1, hours=3)
        self.clock.advance(days=4)
        self.m.complete_task(self.t1.task_id)
        self.assertEqual(self.m.user_penalty(self.anna.user_id), 10 + 5 + 3)
        self.assertEqual(len(self.m.tracker.ledger.for_user(self.anna.user_id)), 2)

    def test_unassigned_task_no_penalty(self):
        t = self.m.create_task("Ничья", "d", Priority.LOW, self.due)
        self.clock.advance(days=10)
        self.assertEqual(self.m.complete_task(t.task_id), [])

    def test_custom_policy(self):
        m = TimedTaskManager(PenaltyPolicy(late_base=1, late_per_day=0), self.clock)
        u = m.create_user("Ян", "yan@company.com")
        t = m.create_task("T", "d", Priority.LOW, self.clock.now + timedelta(days=1))
        m.assign_task(t.task_id, u.user_id)
        self.clock.advance(days=9)
        self.assertEqual(m.complete_task(t.task_id)[0].points, 1)

    def test_bad_estimate_rejected(self):
        with self.assertRaises(ValueError):
            self.m.tracker.set_estimate(self.t1.task_id, timedelta(0))


if __name__ == "__main__":
    unittest.main()
