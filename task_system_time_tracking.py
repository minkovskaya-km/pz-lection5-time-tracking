"""
task_system_time_tracking.py — переработанная версия: модуль учёта времени
для системы управления задач (практическое задание к лекции №5).

Файл работает вместе с task_system_merged.py (положите их в одну папку):
из него берутся готовые классы TaskManager, Task, User, Status, Priority.
Так выполняется требование «интеграция с существующей системой задач».

Соответствие требованиям задания
--------------------------------
1. Старт/остановка таймера для задачи ... TimeTracker.start_timer / stop_timer
2. Учёт общего затраченного времени ..... TimeTracker.total_time / user_time
3. Генерация отчётов по времени ......... TimeTracker.generate_time_report,
                                          format_report_text
4. Интеграция с системой задач .......... TimedTaskManager (наследник TaskManager)
Дополнительно по просьбе преподавателя:
   пользователи ........................ TimedTaskManager.create_user
                                          (проверка имени и уникального e-mail)
   система штрафов ..................... PenaltyPolicy, PenaltyLedger

Правила работы таймера
----------------------
* Таймер запускает пользователь только на свою (назначенную ему) задачу.
* У одного пользователя не может быть двух запущенных таймеров одновременно.
* На завершённой задаче (Status.DONE) таймер запустить нельзя.
* Запуск таймера на задаче в статусе «To Do» переводит её в «In Progress».
* Забытый таймер (дольше max_session, по умолчанию 8 ч) останавливается
  автоматически на границе лимита, а пользователь получает штраф.

Система штрафов (значения можно менять в PenaltyPolicy)
-------------------------------------------------------
| Причина                    | Когда начисляется                       | Баллы             |
|----------------------------|-----------------------------------------|-------------------|
| LATE_COMPLETION            | задача закрыта после срока              | 10 + 5 за каждые  |
|                            |                                         | полные сутки      |
| FORGOTTEN_TIMER            | сессия таймера дольше max_session       | 5 за сессию       |
| OVER_ESTIMATE              | затрачено больше оценки более чем       | 3                 |
|                            | на 20 % (если оценка задана)            |                   |

Штрафы хранятся в журнале (PenaltyLedger) с причиной, задачей и временем.

Использование
-------------
    manager = TimedTaskManager()
    user = manager.create_user("Алексей", "alexey@company.com")
    task = manager.create_task("API", "REST API", Priority.HIGH,
                               datetime.now() + timedelta(days=3))
    manager.assign_task(task.task_id, user.user_id)
    manager.start_timer(user.user_id, task.task_id)
    ...
    manager.stop_timer(user.user_id)
    manager.complete_task(task.task_id)
    print(manager.time_report_text())

Запуск:  python task_system_time_tracking.py   (демонстрация)
Тесты:   python -m unittest discover -v         (файлы test_*.py)
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from task_system_merged import Priority, Status, Task, TaskManager, User

Clock = Callable[[], datetime]


# --------------------------------------------------------------------------
# Исключения
# --------------------------------------------------------------------------
class TimeTrackingError(Exception):
    """Базовая ошибка модуля учёта времени."""


class UnknownUserError(TimeTrackingError):
    """Пользователь не найден."""


class UnknownTaskError(TimeTrackingError):
    """Задача не найдена."""


class NotAssignedError(TimeTrackingError):
    """Задача не назначена этому пользователю."""


class TaskClosedError(TimeTrackingError):
    """Операция недопустима: задача уже завершена."""


class TimerAlreadyRunningError(TimeTrackingError):
    """У пользователя уже есть запущенный таймер."""


class NoActiveTimerError(TimeTrackingError):
    """У пользователя нет запущенного таймера."""


# --------------------------------------------------------------------------
# Данные
# --------------------------------------------------------------------------
@dataclass
class TimeEntry:
    """Одна сессия работы над задачей (от старта до остановки)."""
    entry_id: int
    task_id: int
    user_id: int
    start: datetime
    end: Optional[datetime] = None
    auto_stopped: bool = False   # True, если остановлена по лимиту (забыт таймер)

    @property
    def is_running(self) -> bool:
        return self.end is None

    def duration(self, now: Optional[datetime] = None) -> timedelta:
        """Длительность; для запущенного таймера считается до момента now."""
        end = self.end or now
        if end is None:
            raise ValueError("Для запущенного таймера нужно передать now")
        return end - self.start


class PenaltyReason(Enum):
    LATE_COMPLETION = "Задача закрыта после срока"
    FORGOTTEN_TIMER = "Забытый таймер"
    OVER_ESTIMATE = "Превышение оценки времени"


@dataclass
class Penalty:
    """Начисленный штраф."""
    user_id: int
    task_id: int
    reason: PenaltyReason
    points: int
    created_at: datetime
    comment: str = ""


@dataclass
class PenaltyPolicy:
    """Правила начисления штрафов (все значения настраиваемые)."""
    late_base: int = 10                 # штраф за просрочку
    late_per_day: int = 5               # + за каждые полные сутки просрочки
    max_session: timedelta = timedelta(hours=8)
    forgotten_timer: int = 5
    estimate_tolerance: float = 0.2     # допустимое превышение оценки, 20 %
    over_estimate: int = 3


class PenaltyLedger:
    """Журнал штрафов пользователей."""

    def __init__(self) -> None:
        self._items: List[Penalty] = []

    def add(self, penalty: Penalty) -> Penalty:
        self._items.append(penalty)
        return penalty

    def for_user(self, user_id: int) -> List[Penalty]:
        return [p for p in self._items if p.user_id == user_id]

    def total(self, user_id: int) -> int:
        """Сумма штрафных баллов пользователя."""
        return sum(p.points for p in self.for_user(user_id))

    def all(self) -> List[Penalty]:
        return list(self._items)


def format_duration(delta: timedelta) -> str:
    """Формат Ч:ММ:СС (часы могут быть больше 24)."""
    seconds = int(delta.total_seconds())
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    return f"{sign}{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


# --------------------------------------------------------------------------
# Учёт времени
# --------------------------------------------------------------------------
class TimeTracker:
    """Таймеры, учёт времени и штрафы поверх существующего TaskManager."""

    def __init__(self, manager: TaskManager,
                 policy: Optional[PenaltyPolicy] = None,
                 clock: Clock = datetime.now):
        self.manager = manager
        self.policy = policy or PenaltyPolicy()
        self.ledger = PenaltyLedger()
        self._clock = clock
        self._entries: List[TimeEntry] = []
        self._active: Dict[int, TimeEntry] = {}      # user_id -> запущенная сессия
        self._estimates: Dict[int, timedelta] = {}   # task_id -> оценка
        self._next_entry_id = 1

    # ----- проверки --------------------------------------------------------
    def _get_user(self, user_id: int) -> User:
        user = self.manager.users.get(user_id)
        if user is None:
            raise UnknownUserError(f"Пользователь {user_id} не найден")
        return user

    def _get_task(self, task_id: int) -> Task:
        task = self.manager.tasks.get(task_id)
        if task is None:
            raise UnknownTaskError(f"Задача {task_id} не найдена")
        return task

    # ----- таймер ----------------------------------------------------------
    def start_timer(self, user_id: int, task_id: int) -> TimeEntry:
        """Запустить таймер пользователя на задаче."""
        self._get_user(user_id)
        task = self._get_task(task_id)
        self.check_forgotten_timers()          # забытый таймер не блокирует работу
        if task.assignee is None or task.assignee.user_id != user_id:
            raise NotAssignedError(
                f"Задача {task_id} не назначена пользователю {user_id}")
        if task.status == Status.DONE:
            raise TaskClosedError(f"Задача {task_id} уже завершена")
        if user_id in self._active:
            raise TimerAlreadyRunningError(
                f"У пользователя {user_id} уже запущен таймер на задаче "
                f"{self._active[user_id].task_id}")
        if task.status == Status.TODO:
            task.update_status(Status.IN_PROGRESS)
        entry = TimeEntry(self._next_entry_id, task_id, user_id, self._clock())
        self._next_entry_id += 1
        self._entries.append(entry)
        self._active[user_id] = entry
        return entry

    def stop_timer(self, user_id: int) -> TimeEntry:
        """Остановить таймер пользователя. Если сессия длиннее лимита —
        она обрезается по лимиту, а пользователю начисляется штраф."""
        self._get_user(user_id)
        entry = self._active.get(user_id)
        if entry is None:
            raise NoActiveTimerError(f"У пользователя {user_id} нет запущенного таймера")
        now = self._clock()
        if now - entry.start > self.policy.max_session:
            self._auto_stop(entry, now)
        else:
            self._close(entry, now)
        return entry

    def active_timer(self, user_id: int) -> Optional[TimeEntry]:
        """Запущенный таймер пользователя или None."""
        return self._active.get(user_id)

    def check_forgotten_timers(self) -> List[TimeEntry]:
        """Остановить все таймеры, работающие дольше лимита (штраф каждому).
        Метод можно вызывать периодически (например, раз в час)."""
        now = self._clock()
        stopped = []
        for entry in list(self._active.values()):
            if now - entry.start > self.policy.max_session:
                self._auto_stop(entry, now)
                stopped.append(entry)
        return stopped

    def _close(self, entry: TimeEntry, end: datetime) -> None:
        entry.end = end
        self._active.pop(entry.user_id, None)

    def _auto_stop(self, entry: TimeEntry, now: datetime) -> None:
        limit = self.policy.max_session
        self._close(entry, entry.start + limit)
        entry.auto_stopped = True
        self.ledger.add(Penalty(
            entry.user_id, entry.task_id, PenaltyReason.FORGOTTEN_TIMER,
            self.policy.forgotten_timer, now,
            f"сессия дольше {format_duration(limit)}, обрезана по лимиту"))

    # ----- учёт времени ----------------------------------------------------
    def entries(self, task_id: Optional[int] = None,
                user_id: Optional[int] = None) -> List[TimeEntry]:
        """Все сессии, при необходимости отфильтрованные по задаче/пользователю."""
        return [e for e in self._entries
                if (task_id is None or e.task_id == task_id)
                and (user_id is None or e.user_id == user_id)]

    def total_time(self, task_id: int, include_running: bool = True) -> timedelta:
        """Общее время по задаче (включая идущую сессию, если include_running)."""
        self._get_task(task_id)
        return self._sum(self.entries(task_id=task_id), include_running)

    def user_time(self, user_id: int, include_running: bool = True) -> timedelta:
        """Общее время пользователя по всем задачам."""
        self._get_user(user_id)
        return self._sum(self.entries(user_id=user_id), include_running)

    def _sum(self, entries: List[TimeEntry], include_running: bool) -> timedelta:
        now = self._clock()
        total = timedelta()
        for e in entries:
            if e.is_running and not include_running:
                continue
            total += e.duration(now)
        return total

    def set_estimate(self, task_id: int, estimate: timedelta) -> None:
        """Задать оценку времени на задачу (нужна для штрафа OVER_ESTIMATE)."""
        self._get_task(task_id)
        if estimate <= timedelta(0):
            raise ValueError("Оценка должна быть положительной")
        self._estimates[task_id] = estimate

    # ----- штрафы при завершении -------------------------------------------
    def evaluate_completion(self, task_id: int) -> List[Penalty]:
        """Проверить завершаемую задачу и начислить штрафы исполнителю
        (просрочка и превышение оценки). Возвращает новые штрафы."""
        task = self._get_task(task_id)
        if task.assignee is None:
            return []
        now = self._clock()
        uid = task.assignee.user_id
        new: List[Penalty] = []
        if now > task.due_date:
            days = (now - task.due_date).days
            points = self.policy.late_base + self.policy.late_per_day * days
            new.append(Penalty(uid, task_id, PenaltyReason.LATE_COMPLETION,
                               points, now, f"просрочка {days} сут."))
        estimate = self._estimates.get(task_id)
        if estimate is not None:
            spent = self.total_time(task_id, include_running=False)
            if spent > estimate * (1 + self.policy.estimate_tolerance):
                new.append(Penalty(
                    uid, task_id, PenaltyReason.OVER_ESTIMATE,
                    self.policy.over_estimate, now,
                    f"затрачено {format_duration(spent)} при оценке "
                    f"{format_duration(estimate)}"))
        for p in new:
            self.ledger.add(p)
        return new

    # ----- отчёты ----------------------------------------------------------
    def generate_time_report(self, date_from: Optional[datetime] = None,
                             date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """Отчёт по времени. В отчёт попадают сессии, начавшиеся в периоде
        [date_from, date_to); без границ — все сессии."""
        now = self._clock()
        selected = [e for e in self._entries
                    if (date_from is None or e.start >= date_from)
                    and (date_to is None or e.start < date_to)]
        by_task: Dict[int, timedelta] = {}
        by_user: Dict[int, timedelta] = {}
        for e in selected:
            d = e.duration(now)
            by_task[e.task_id] = by_task.get(e.task_id, timedelta()) + d
            by_user[e.user_id] = by_user.get(e.user_id, timedelta()) + d
        return {
            "period": {"from": date_from.isoformat() if date_from else None,
                       "to": date_to.isoformat() if date_to else None},
            "total_time": format_duration(sum(by_task.values(), timedelta())),
            "sessions": len(selected),
            "running_timers": sum(1 for e in selected if e.is_running),
            "by_task": [{"task_id": t, "title": self.manager.tasks[t].title,
                         "time": format_duration(d)}
                        for t, d in sorted(by_task.items())],
            "by_user": [{"user_id": u, "name": self.manager.users[u].name,
                         "time": format_duration(d),
                         "penalty_points": self.ledger.total(u)}
                        for u, d in sorted(by_user.items())],
            "penalties": [{"user_id": p.user_id, "task_id": p.task_id,
                           "reason": p.reason.value, "points": p.points,
                           "comment": p.comment}
                          for p in self.ledger.all()],
            "generated_at": now.isoformat(),
        }

    @staticmethod
    def format_report_text(report: Dict[str, Any]) -> str:
        """Текстовый вид отчёта по времени."""
        lines = ["ОТЧЁТ ПО ВРЕМЕНИ",
                 f"Всего: {report['total_time']}  (сессий: {report['sessions']}, "
                 f"запущено: {report['running_timers']})",
                 "", "По задачам:"]
        lines += [f"  #{r['task_id']} {r['title']}: {r['time']}"
                  for r in report["by_task"]] or ["  —"]
        lines += ["", "По пользователям:"]
        lines += [f"  {r['name']}: {r['time']}, штрафы: {r['penalty_points']}"
                  for r in report["by_user"]] or ["  —"]
        lines += ["", "Штрафы:"]
        lines += [f"  пользователь {p['user_id']}, задача {p['task_id']}: "
                  f"{p['reason']} (+{p['points']}) {p['comment']}"
                  for p in report["penalties"]] or ["  нет"]
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Интеграция с системой задач
# --------------------------------------------------------------------------
class TimedTaskManager(TaskManager):
    """TaskManager с таймерами, учётом времени и штрафами."""

    def __init__(self, policy: Optional[PenaltyPolicy] = None,
                 clock: Clock = datetime.now):
        super().__init__()
        self._clock = clock
        self.tracker = TimeTracker(self, policy, clock)

    def create_user(self, name: str, email: str) -> User:
        """Создание пользователя с проверкой имени и уникальности e-mail."""
        name, email = name.strip(), email.strip().lower()
        if not name:
            raise ValueError("Имя пользователя не может быть пустым")
        if "@" not in email:
            raise ValueError("Некорректный e-mail")
        if any(u.email.lower() == email for u in self.users.values()):
            raise ValueError(f"Пользователь с e-mail {email} уже существует")
        return super().create_user(name, email)

    def start_timer(self, user_id: int, task_id: int) -> TimeEntry:
        return self.tracker.start_timer(user_id, task_id)

    def stop_timer(self, user_id: int) -> TimeEntry:
        return self.tracker.stop_timer(user_id)

    def complete_task(self, task_id: int) -> List[Penalty]:
        """Завершить задачу: остановить её таймеры, начислить штрафы,
        перевести в Done. Возвращает начисленные штрафы."""
        task = self.tracker._get_task(task_id)
        if task.status == Status.DONE:
            raise TaskClosedError(f"Задача {task_id} уже завершена")
        for entry in list(self.tracker._active.values()):
            if entry.task_id == task_id:
                self.tracker.stop_timer(entry.user_id)
        penalties = self.tracker.evaluate_completion(task_id)
        task.update_status(Status.DONE)
        return penalties

    def user_penalty(self, user_id: int) -> int:
        """Сумма штрафных баллов пользователя."""
        return self.tracker.ledger.total(user_id)

    def generate_report(self) -> Dict:
        """Отчёт по задачам из лекции + раздел с временем."""
        report = super().generate_report()
        report["time"] = self.tracker.generate_time_report()
        return report

    def time_report_text(self, date_from: Optional[datetime] = None,
                         date_to: Optional[datetime] = None) -> str:
        return TimeTracker.format_report_text(
            self.tracker.generate_time_report(date_from, date_to))


# --------------------------------------------------------------------------
# Демонстрация
# --------------------------------------------------------------------------
def demo() -> None:
    class Clock:                       # управляемые часы для демонстрации
        now = datetime(2026, 1, 12, 9, 0)

        def __call__(self) -> datetime:
            return self.now

        def advance(self, **kw: float) -> None:
            self.now += timedelta(**kw)

    clock = Clock()
    m = TimedTaskManager(clock=clock)
    anna = m.create_user("Анна Соколова", "anna@company.com")
    boris = m.create_user("Борис Ким", "boris@company.com")
    api = m.create_task("Разработать REST API", "API задач", Priority.HIGH,
                        clock.now + timedelta(days=2))
    tests = m.create_task("Написать тесты", "unit-тесты", Priority.MEDIUM,
                          clock.now + timedelta(days=5))
    m.assign_task(api.task_id, anna.user_id)
    m.assign_task(tests.task_id, boris.user_id)
    m.tracker.set_estimate(api.task_id, timedelta(hours=4))

    m.start_timer(anna.user_id, api.task_id)       # Анна работает 3 часа
    clock.advance(hours=3)
    m.stop_timer(anna.user_id)
    m.start_timer(boris.user_id, tests.task_id)    # Борис забыл выключить таймер
    clock.advance(hours=14)
    m.start_timer(anna.user_id, api.task_id)       # ещё 2 часа -> перерасход
    clock.advance(hours=2)
    m.complete_task(api.task_id)                   # в срок, но 5 ч при оценке 4 ч
    clock.advance(days=6)
    m.complete_task(tests.task_id)                 # закрыта с просрочкой 1 сутки

    print(m.time_report_text())


if __name__ == "__main__":
    demo()
    print("\nТесты лежат в файлах test_*.py: python -m unittest discover -v")
