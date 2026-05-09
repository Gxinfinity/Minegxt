from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress


def fire_and_forget(coro: Awaitable[object]) -> asyncio.Task[object]:
    task = asyncio.create_task(coro)
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    return task


async def maybe_call(fn: Callable[..., object], *args: object, **kwargs: object) -> object:
    result = fn(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


async def safe_remove(path) -> None:
    with suppress(Exception):
        path.unlink(missing_ok=True)
