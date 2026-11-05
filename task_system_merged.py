"""
task_system_merged.py — объединяющий файл.

Здесь собран в один рабочий модуль весь код из лекции №5
«Этапы разработки программного продукта»:

    2.1 Сбор и анализ требований   -> TaskRequirement
    2.2 Проектирование             -> Priority, Status, User, Task
    2.3 Реализация                 -> TaskManager
    2.4 Тестирование               -> test_merged_system.py (unittest)
    2.5 Внедрение                  -> DeploymentManager
    2.6 Сопровождение              -> MonitoringSystem, MonitoredTaskManager
    3.1 Agile                      -> KanbanBoard

Что изменено по сравнению с лекцией (чтобы всё запускалось):
  * код лекции лежал в разных фрагментах, здесь он в одном файле и в
    правильном порядке (Task/User объявлены до TaskManager и KanbanBoard);
  * в MonitoredTaskManager декоратор из лекции
    (@MonitoringSystem.measure_performance.__func__('...')) не работает,
    потому что требует экземпляр MonitoringSystem. Теперь методы
    оборачиваются в __init__ через self.monitor.measure_performance;
  * в DeploymentManager.run_tests тесты берутся из этого же файла,
    а не из несуществующего test_task_system.py;
  * демонстрации вынесены в функции и запускаются только из __main__.

Запуск:  python task_system_merged.py                  (демонстрация)
Тесты:   python -m unittest test_merged_system -v
"""
import json
import logging
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------
# 2.1 Сбор и анализ требований
# --------------------------------------------------------------------------
class TaskRequirement:
    """Требование к системе (функциональное или нефункциональное)."""

    def __init__(self, description: str, priority: str, category: str):
        self.description = description
        self.priority = priority      # High, Medium, Low
        self.category = category      # Functional, Non-functional

    def validate(self) -> bool:
        """Валидация требования."""
        if not self.description:
            raise ValueError("Требование должно иметь описание")
        return True


# --------------------------------------------------------------------------
# 2.2 Проектирование
# --------------------------------------------------------------------------
class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Status(Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"


class User:
    """Пользователь системы."""

    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

    def __str__(self) -> str:
        return f"User({self.name}, {self.email})"


class Task:
    """Задача."""

    def __init__(self, task_id: int, title: str, description: str,
                 priority: Priority, due_date: datetime):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.priority = priority
        self.due_date = due_date
        self.status = Status.TODO
        self.assignee: Optional[User] = None
        self.created_at = datetime.now()

    def assign_to(self, user: User) -> None:
        """Назначение задачи пользователю."""
        self.assignee = user
        self.status = Status.IN_PROGRESS

    def update_status(self, new_status: Status) -> None:
        """Обновление статуса задачи."""
        self.status = new_status

    def is_overdue(self) -> bool:
        """Проверка просрочки задачи."""
        return datetime.now() > self.due_date

    def __str__(self) -> str:
        return f"Task '{self.title}' ({self.status.value})"


# --------------------------------------------------------------------------
# 2.3 Реализация
# --------------------------------------------------------------------------
class TaskManager:
    """Класс для управления задачами."""

    def __init__(self):
        self.tasks: Dict[int, Task] = {}
        self.users: Dict[int, User] = {}
        self.next_task_id = 1
        self.next_user_id = 1

    def create_user(self, name: str, email: str) -> User:
        """Создание нового пользователя."""
        user = User(self.next_user_id, name, email)
        self.users[self.next_user_id] = user
        self.next_user_id += 1
        return user

    def create_task(self, title: str, description: str,
                    priority: Priority, due_date: datetime) -> Task:
        """Создание новой задачи."""
        task = Task(self.next_task_id, title, description, priority, due_date)
        self.tasks[self.next_task_id] = task
        self.next_task_id += 1
        return task

    def assign_task(self, task_id: int, user_id: int) -> bool:
        """Назначение задачи пользователю."""
        task = self.tasks.get(task_id)
        user = self.users.get(user_id)
        if task and user:
            task.assign_to(user)
            return True
        return False

    def get_overdue_tasks(self) -> List[Task]:
        """Получение списка просроченных задач."""
        return [t for t in self.tasks.values() if t.is_overdue()]

    def get_user_tasks(self, user_id: int) -> List[Task]:
        """Получение задач конкретного пользователя."""
        return [t for t in self.tasks.values()
                if t.assignee and t.assignee.user_id == user_id]

    def generate_report(self) -> Dict:
        """Генерация отчёта по задачам."""
        status_count: Dict[Status, int] = {}
        for task in self.tasks.values():
            status_count[task.status] = status_count.get(task.status, 0) + 1
        return {
            "total_tasks": len(self.tasks),
            "overdue_tasks": len(self.get_overdue_tasks()),
            "status_distribution": {s.value: c for s, c in status_count.items()},
            "report_generated_at": datetime.now().isoformat(),
        }


# --------------------------------------------------------------------------
# 2.5 Внедрение и развёртывание
# --------------------------------------------------------------------------
class DeploymentManager:
    """Менеджер развёртывания системы."""

    def __init__(self, project_path: str, deploy_path: str):
        self.project_path = Path(project_path)
        self.deploy_path = Path(deploy_path)

    def validate_environment(self) -> bool:
        """Проверка окружения для развёртывания."""
        print("Проверка окружения...")
        if sys.version_info < (3, 8):
            print("Ошибка: Требуется Python 3.8 или выше")
            return False
        for name in ["task_system_merged.py"]:
            if not (self.project_path / name).exists():
                print(f"Ошибка: Отсутствует файл {name}")
                return False
        print("Окружение проверено успешно")
        return True

    def install_dependencies(self) -> bool:
        """Установка зависимостей (если есть requirements.txt)."""
        print("Установка зависимостей...")
        req = self.project_path / "requirements.txt"
        if req.exists():
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", str(req)])
            except subprocess.CalledProcessError:
                print("Ошибка при установке зависимостей")
                return False
        return True

    def deploy_files(self) -> bool:
        """Копирование файлов и создание конфигурации."""
        print("Копирование файлов...")
        try:
            self.deploy_path.mkdir(parents=True, exist_ok=True)
            for name in ["task_system_merged.py", "test_merged_system.py", "README.md"]:
                source = self.project_path / name
                if source.exists():
                    shutil.copy2(source, self.deploy_path / name)
                    print(f"Скопирован {name}")
            config = {"database_path": str(self.deploy_path / "tasks.db"),
                      "log_level": "INFO", "max_users": 100}
            with open(self.deploy_path / "config.json", "w",
                      encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            print("Конфигурационный файл создан")
            return True
        except OSError as e:
            print(f"Ошибка при копировании файлов: {e}")
            return False

    def run_tests(self) -> bool:
        """Запуск тестов после развёртывания."""
        print("Запуск тестов...")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "test_merged_system"],
            cwd=self.deploy_path, capture_output=True, text=True)
        if result.returncode == 0:
            print("Все тесты пройдены успешно")
            return True
        print("Некоторые тесты не пройдены:")
        print(result.stderr)
        return False

    def deploy(self) -> bool:
        """Основной процесс развёртывания."""
        print("Начало процесса развёртывания...")
        steps = [("Проверка окружения", self.validate_environment),
                 ("Установка зависимостей", self.install_dependencies),
                 ("Копирование файлов", self.deploy_files),
                 ("Запуск тестов", self.run_tests)]
        for step_name, step_func in steps:
            print(f"\n--- {step_name} ---")
            if not step_func():
                print(f"Развёртывание прервано на этапе: {step_name}")
                return False
        print(f"\nСистема развёрнута в: {self.deploy_path}")
        return True


# --------------------------------------------------------------------------
# 2.6 Сопровождение и поддержка
# --------------------------------------------------------------------------
class MonitoringSystem:
    """Система мониторинга для сопровождения ПО."""

    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger("TaskManager")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler: logging.Handler = (logging.FileHandler(log_file)
                                        if log_file else logging.StreamHandler())
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(handler)
        self.performance_metrics: Dict[str, Any] = {
            "response_times": [], "error_count": 0, "tasks_created": 0}

    def log_operation(self, operation: str, duration: Optional[float] = None,
                      success: bool = True) -> None:
        """Логирование операций."""
        if duration is not None:
            self.performance_metrics["response_times"].append(duration)
        if not success:
            self.performance_metrics["error_count"] += 1
        if operation == "create_task":
            self.performance_metrics["tasks_created"] += 1
        level = logging.INFO if success else logging.ERROR
        self.logger.log(
            level, f"Operation: {operation}, Duration: {duration or 0:.3f}s, "
                   f"Success: {success}")

    def measure_performance(self, operation_name: str):
        """Декоратор для измерения производительности."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    self.log_operation(operation_name, time.time() - start, True)
                    return result
                except Exception:
                    self.log_operation(operation_name, time.time() - start, False)
                    raise
            return wrapper
        return decorator

    def generate_maintenance_report(self) -> Dict[str, Any]:
        """Генерация отчёта для сопровождения."""
        times = self.performance_metrics["response_times"]
        avg = sum(times) / len(times) if times else 0
        return {
            "timestamp": datetime.now().isoformat(),
            "performance_metrics": {
                "average_response_time": avg,
                "total_operations": len(times),
                "error_rate": self.performance_metrics["error_count"]
                              / max(len(times), 1),
                "total_tasks_created": self.performance_metrics["tasks_created"],
            },
            "recommendations": self.generate_recommendations(avg),
        }

    def generate_recommendations(self, avg_response_time: float) -> List[str]:
        """Генерация рекомендаций по улучшению."""
        rec: List[str] = []
        if avg_response_time > 1.0:
            rec.append("Рассмотреть оптимизацию базы данных - высокое время ответа")
        if self.performance_metrics["error_count"] > 10:
            rec.append("Провести анализ ошибок - высокий уровень ошибок")
        if self.performance_metrics["tasks_created"] > 1000:
            rec.append("Рассмотреть масштабирование системы - высокий уровень использования")
        return rec or ["Система работает стабильно"]


class MonitoredTaskManager(TaskManager):
    """TaskManager с мониторингом (исправленный вариант из лекции)."""

    def __init__(self):
        super().__init__()
        self.monitor = MonitoringSystem()
        self.create_task = self.monitor.measure_performance("create_task")(
            self.create_task)
        self.assign_task = self.monitor.measure_performance("assign_task")(
            self.assign_task)


# --------------------------------------------------------------------------
# 3.1 Agile: Канбан-доска
# --------------------------------------------------------------------------
@dataclass
class KanbanBoard:
    """Канбан-доска для Agile управления."""
    todo: List[Task] = field(default_factory=list)
    in_progress: List[Task] = field(default_factory=list)
    review: List[Task] = field(default_factory=list)
    done: List[Task] = field(default_factory=list)

    def move_task(self, task: Task, from_column: str, to_column: str) -> None:
        """Перемещение задачи между колонками."""
        getattr(self, from_column).remove(task)
        getattr(self, to_column).append(task)
        mapping = {"todo": Status.TODO, "in_progress": Status.IN_PROGRESS,
                   "review": Status.REVIEW, "done": Status.DONE}
        task.update_status(mapping[to_column])

    def get_board_stats(self) -> Dict:
        """Статистика по доске."""
        total = (len(self.todo) + len(self.in_progress)
                 + len(self.review) + len(self.done))
        return {"todo": len(self.todo), "in_progress": len(self.in_progress),
                "review": len(self.review), "done": len(self.done),
                "completion_rate": len(self.done) / max(total, 1)}


# --------------------------------------------------------------------------
# Демонстрация
# --------------------------------------------------------------------------
def demo_implementation() -> None:
    manager = TaskManager()
    developer = manager.create_user("Алексей Кодлов", "alexey@company.com")
    tester = manager.create_user("Елена Тестова", "elena@company.com")
    t1 = manager.create_task("Разработать REST API", "Создать API для задач",
                             Priority.HIGH, datetime.now() + timedelta(days=14))
    t2 = manager.create_task("Написать unit-тесты", "Покрыть код тестами",
                             Priority.MEDIUM, datetime.now() + timedelta(days=7))
    manager.assign_task(t1.task_id, developer.user_id)
    manager.assign_task(t2.task_id, tester.user_id)
    print("Отчёт по задачам:")
    print(json.dumps(manager.generate_report(), indent=2, ensure_ascii=False))
    print(f"\nЗадачи разработчика {developer.name}:")
    for task in manager.get_user_tasks(developer.user_id):
        print(f"  - {task.title} ({task.status.value})")


if __name__ == "__main__":
    demo_implementation()
    print("\nТесты: python -m unittest test_merged_system -v")
