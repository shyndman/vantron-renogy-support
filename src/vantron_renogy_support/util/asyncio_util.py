import asyncio
from collections.abc import Awaitable, Callable
from typing import Never, ParamSpec


P = ParamSpec("P")


async def periodic_task(
    interval: float,
    func: Callable[P, Awaitable[object]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> Never:
    """Run func every interval seconds.

    If func has not finished before *interval*, will run again immediately when
    the previous iteration finished.

    *args and **kwargs are passed as the arguments to func.
    """
    while True:
        _ = await asyncio.gather(
            func(*args, **kwargs),
            asyncio.sleep(interval),
        )
