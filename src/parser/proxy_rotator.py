import random
from collections import Counter
from typing import TypeVar, Hashable, Iterable

T = TypeVar("T", bound=Hashable)


class Rotator:
    """
    Simple proxy rotator
    """
    def __init__(self, objects: Iterable[T] = None):
        self._objects = objects
        self._groups: dict[str, Counter] = dict()

    def get(self, resource: str = None) -> T or None:
        """
        Args:
            resource: Название ресурса для которого будет использоваться объект
        """
        if not self._objects:
            return None
        group_counter = self._groups.get(resource)
        if group_counter is None:
            self._groups[resource] = group_counter = Counter(self._objects)
        obj = random.choice([o for o, count in group_counter.items() if count == min(group_counter.values())])
        group_counter[obj] += 1
        return obj

    def release(self, obj: T, group: str = None):
        self._groups[group][obj] -= 1

    def clear(self):
        self._groups = dict()
