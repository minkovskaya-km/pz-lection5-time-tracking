"""Тесты пользователей: создание и проверка имени/e-mail.

Запуск: python -m unittest test_users -v
"""
import unittest
from datetime import timedelta

from task_system_time_tracking import (
    NoActiveTimerError, NotAssignedError, PenaltyPolicy, PenaltyReason,
    Priority, Status, TaskClosedError, TimedTaskManager,
    TimerAlreadyRunningError, UnknownTaskError, UnknownUserError,
    format_duration)
from tt_helpers import TimeTrackingTestCase


class TestUsers(TimeTrackingTestCase):
    def test_create_user_normalizes_and_stores(self):
        u = self.m.create_user("  Вера ", " Vera@Company.com ")
        self.assertEqual((u.name, u.email), ("Вера", "vera@company.com"))
        self.assertIn(u.user_id, self.m.users)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            self.m.create_user("  ", "x@y.com")

    def test_bad_email_rejected(self):
        with self.assertRaises(ValueError):
            self.m.create_user("Вера", "no-at-sign")

    def test_duplicate_email_rejected(self):
        with self.assertRaises(ValueError):
            self.m.create_user("Другая Анна", "ANNA@company.com")


if __name__ == "__main__":
    unittest.main()
