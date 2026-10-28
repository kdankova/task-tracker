from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self

from app.domain.enums import TaskStatus


@dataclass(frozen=True, slots=True)
class TaskStats:
    counts: Mapping[TaskStatus, int]

    @classmethod
    def from_counts(cls, counts: Mapping[TaskStatus, int]) -> Self:
        return cls({status: counts.get(status, 0) for status in TaskStatus})

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def __getitem__(self, status: TaskStatus) -> int:
        return self.counts[status]
