from app.domain.enums import TaskStatus
from app.domain.stats import TaskStats


def test_missing_statuses_are_reported_as_zero() -> None:
    stats = TaskStats.from_counts({TaskStatus.DONE: 2})

    assert dict(stats.counts) == {
        TaskStatus.NEW: 0,
        TaskStatus.IN_PROGRESS: 0,
        TaskStatus.DONE: 2,
        TaskStatus.CANCELLED: 0,
    }


def test_total_is_the_sum_of_all_statuses() -> None:
    stats = TaskStats.from_counts({TaskStatus.NEW: 3, TaskStatus.DONE: 4, TaskStatus.CANCELLED: 1})

    assert stats.total == 8


def test_empty_stats() -> None:
    stats = TaskStats.from_counts({})

    assert stats.total == 0
    assert all(stats[status] == 0 for status in TaskStatus)
