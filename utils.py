import asyncio
import contextlib
import functools


def debounce(wait):
    def decorator(fn):
        @functools.wraps(fn)
        async def debounced(*args, **kwargs):
            debounced._task = getattr(debounced, '_task', None)
            if debounced._task is not None:
                debounced._task.cancel()
            async def task():
                await asyncio.sleep(wait)
                await fn(*args, **kwargs)
            debounced._task = asyncio.create_task(task())
        return debounced
    return decorator
