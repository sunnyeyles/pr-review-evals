"""Retry helper for outbound calls to the notification service.

The notification service is flaky under load and returns 503 fairly often, so
anything that talks to it should go through :func:`with_retries`.
"""

import time
from typing import Callable

BASE_DELAY_SECONDS = 0.2
MAX_DELAY_SECONDS = 5.0


def backoff_delay(attempt: int) -> float:
    """Exponential backoff, capped so a long outage does not stall a worker."""
    return min(BASE_DELAY_SECONDS * (2**attempt), MAX_DELAY_SECONDS)


def with_retries(operation: Callable, attempts: int = 3):
    """Call *operation*, making up to *attempts* calls before giving up.

    Returns whatever *operation* returns. If every call raises, the exception
    from the final call is re-raised.
    """
    last_error = None
    for attempt in range(1, attempts):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            time.sleep(backoff_delay(attempt))
    raise last_error
