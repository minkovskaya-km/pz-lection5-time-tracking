"""Тесты базовой системы задач из лекции (task_system_merged.py).

Запуск: python -m unittest test_merged_system -v
"""
import unittest
from datetime import datetime, timedelta

from task_system_merged import (
    KanbanBoard, MonitoredTaskManager, Priority, Status, TaskManager,
    TaskRequirement)


class TestTaskSystem(unittest.TestCase):
    """Модульные тесты базовой системы задач (из лекции)."""

    def setUp(self):
        self.manager = TaskManager()
        self.user = self.manager.create_user("Тест User", "test@test.com")
        self.due_date = datetime.now() + timedelta(days=5)

    def test_task_creation(self):
        task = self.manager.create_task("Тестовая задача", "Описание",
                                        Priority.MEDIUM, self.due_date)
        self.assertEqual(task.title, "Тестовая задача")
        self.assertEqual(task.status, Status.TODO)
        self.assertIsNone(task.assignee)

    def test_task_assignment(self):
        task = self.manager.create_task("Назначаемая", "Описание",
                                        Priority.HIGH, self.due_date)
        self.assertTrue(self.manager.assign_task(task.task_id, self.user.user_id))
        self.assertEqual(task.assignee.user_id, self.user.user_id)
        self.assertEqual(task.status, Status.IN_PROGRESS)

    def test_overdue_detection(self):
        past = datetime.now() - timedelta(days=1)
        task = self.manager.create_task("Просроченная", "Описание",
                                        Priority.LOW, past)
        self.assertIn(task, self.manager.get_overdue_tasks())

    def test_user_tasks_retrieval(self):
        t1 = self.manager.create_task("Задача 1", "Описание 1",
                                      Priority.MEDIUM, self.due_date)
        t2 = self.manager.create_task("Задача 2", "Описание 2",
                                      Priority.LOW, self.due_date)
        self.manager.assign_task(t1.task_id, self.user.user_id)
        self.manager.assign_task(t2.task_id, self.user.user_id)
        self.assertEqual(len(self.manager.get_user_tasks(self.user.user_id)), 2)

    def test_report_generation(self):
        for i in range(3):
            self.manager.create_task(f"Задача {i}", f"Описание {i}",
                                     Priority.MEDIUM, self.due_date)
        report = self.manager.generate_report()
        self.assertEqual(report["total_tasks"], 3)
        self.assertEqual(report["status_distribution"]["To Do"], 3)

    def test_requirement_validation(self):
        self.assertTrue(TaskRequirement("Создавать задачи", "High",
                                        "Functional").validate())
        with self.assertRaises(ValueError):
            TaskRequirement("", "High", "Functional").validate()

    def test_kanban_move(self):
        task = self.manager.create_task("Канбан", "Описание",
                                        Priority.LOW, self.due_date)
        board = KanbanBoard(todo=[task])
        board.move_task(task, "todo", "done")
        self.assertEqual(task.status, Status.DONE)
        self.assertEqual(board.get_board_stats()["completion_rate"], 1.0)

    def test_monitored_manager(self):
        manager = MonitoredTaskManager()
        manager.create_task("Задача", "Описание", Priority.LOW, self.due_date)
        self.assertEqual(manager.monitor.performance_metrics["tasks_created"], 1)


if __name__ == "__main__":
    unittest.main()
