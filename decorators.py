import asyncio
import functools
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Optional
from typing import Tuple
from typing import Union

from logger import get_logger
from utils import time_difference


logger = get_logger(__name__)


def delayed(until: Optional[time] = None):
    def delayed_decorator(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            if until is not None:
                wait_for = time_difference(datetime.now().time(), until)
                logger.info('send_inspirational_message, waiting for: %s hours, %s minutes', wait_for.seconds // 3600, wait_for.seconds // 60 % 60)
                await asyncio.sleep(wait_for.total_seconds())
            return await func(*args, **kwargs)
        return inner
    return delayed_decorator


def run_every(hours: int = 0, minutes: int = 0, at: Union[Tuple[int, int], str, None] = None):
    t = None
    if isinstance(at, tuple):
        t = time(*at)
    elif isinstance(at, str):
        h, m = map(int, at.split(':'))
        t = time(h, m)

    def run_every__decorator(func):
        func.scheduled_every = timedelta(hours=hours, minutes=minutes)
        func.scheduled_at = t
        return delayed(until=t)(func)
    return run_every__decorator


def daily(at: Union[Tuple[int, int], str, None] = None):
    return run_every(hours=24, at=at)
