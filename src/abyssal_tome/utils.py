import asyncio
import functools


def debounce(wait):
    """
    Decorator that debounces an asynchronous function, ensuring it is called only once after a specified delay.
    
    Parameters:
        wait (float): The delay in seconds to wait after the last call before executing the function.
    
    Returns:
        Callable: A decorator that wraps an async function, delaying its execution and canceling any previous pending calls within the wait period.
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def debounced(*args, **kwargs) -> None:
            debounced._task = getattr(debounced, "_task", None)
            if debounced._task is not None:
                debounced._task.cancel()

            async def task() -> None:
                await asyncio.sleep(wait)
                await fn(*args, **kwargs)

            debounced._task = asyncio.create_task(task())

        return debounced

    return decorator
