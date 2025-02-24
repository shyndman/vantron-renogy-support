import asyncio
from typing import Iterable


async def periodic_task(interval: float, func, *args, **kwargs):
    """Run func every interval seconds.

    If func has not finished before *interval*, will run again immediately when
    the previous iteration finished.

    *args and **kwargs are passed as the arguments to func.
    """
    while True:
        await asyncio.gather(
            func(*args, **kwargs),
            asyncio.sleep(interval),
        )
