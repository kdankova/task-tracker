from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: Sequence[T]
    total: int
    limit: int
    offset: int
