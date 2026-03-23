from collections.abc import Callable
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def retry_on_exception(
    *,
    attempts: int = 3,
    multiplier: float = 1,
    min_wait: float = 1,
    max_wait: float = 10,
    exception_type: type[Exception] = Exception,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return retry(
        retry=retry_if_exception_type(exception_type),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        reraise=True,
    )
