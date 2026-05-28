import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, Set


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: Set[asyncio.Task[Any]] = set()
        self._logger = logging.getLogger("lifecycle")

    def create_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        task: asyncio.Task[Any] = asyncio.create_task(coro)
        self._tasks.add(task)

        def _on_done(t: asyncio.Task[Any]) -> None:
            self._tasks.discard(t)

        task.add_done_callback(_on_done)
        return task

    def get_tracked_tasks(self) -> Set[asyncio.Task[Any]]:
        return set(self._tasks)

    async def flush_all_tasks_async(self, timeout: float = 5.0) -> None:
        if not self._tasks:
            return

        tasks = [t for t in self._tasks if not t.done()]
        if not tasks:
            return

        self._logger.info("Shutting down %d background tasks", len(tasks))
        for t in tasks:
            try:
                t.cancel()
            except Exception:
                pass

        try:
            await asyncio.wait(tasks, timeout=timeout)
        except Exception:
            self._logger.exception("Error while waiting for background tasks")


# Module-level registry for convenience
task_registry = TaskRegistry()


def create_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    return task_registry.create_task(coro)


def get_tracked_tasks() -> Set[asyncio.Task[Any]]:
    return task_registry.get_tracked_tasks()


async def shutdown(timeout: float = 5.0) -> None:
    return await task_registry.flush_all_tasks_async(timeout=timeout)
