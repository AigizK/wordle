from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import Settings
from app.services.time_service import day_index


@dataclass(frozen=True)
class TaskItem:
    word: str
    description: str


@lru_cache(maxsize=8)
def _load_dictionary_cached(path_str: str, mtime: float) -> frozenset[str]:
    path = Path(path_str)
    words: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        word = raw.strip().lower()
        if not word:
            continue
        if len(word) != 5:
            raise ValueError(f"Dictionary contains non-5-char word: {word}")
        words.append(word)
    return frozenset(words)


@lru_cache(maxsize=8)
def _load_tasks_cached(path_str: str, mtime: float) -> tuple[TaskItem, ...]:
    path = Path(path_str)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Tasks file must be a JSON array")

    tasks: list[TaskItem] = []
    seen: set[str] = set()
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Task #{idx} must be an object")
        word = str(item.get("word", "")).strip().lower()
        description = str(item.get("description", "")).strip()
        if len(word) != 5:
            raise ValueError(f"Task #{idx} has invalid word length: {word}")
        if not description:
            raise ValueError(f"Task #{idx} has empty description")
        if word in seen:
            raise ValueError(f"Duplicate task word found: {word}")
        seen.add(word)
        tasks.append(TaskItem(word=word, description=description))
    return tuple(tasks)


def load_dictionary(settings: Settings) -> frozenset[str]:
    path = settings.dictionary_path
    return _load_dictionary_cached(str(path), path.stat().st_mtime)


def load_tasks(settings: Settings) -> tuple[TaskItem, ...]:
    path = settings.tasks_path
    return _load_tasks_cached(str(path), path.stat().st_mtime)


def task_for_day(settings: Settings, day) -> tuple[int, TaskItem] | None:
    idx = day_index(settings, day)
    tasks = load_tasks(settings)
    if idx < 0 or idx >= len(tasks):
        return None
    return idx, tasks[idx]


def task_for_day_index(settings: Settings, idx: int) -> TaskItem | None:
    tasks = load_tasks(settings)
    if idx < 0 or idx >= len(tasks):
        return None
    return tasks[idx]
