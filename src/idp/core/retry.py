"""Retry utilities with exponential backoff."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import ParamSpec, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from idp.core.logging import get_logger

P = ParamSpec("P")
T = TypeVar("T")

logger = get_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )

    def should_retry(self, exception: Exception) -> bool:
        """Check if an exception should trigger a retry."""
        # Check if it's a retryable exception type
        if not isinstance(exception, self.retryable_exceptions):
            return False

        # Check for specific retryable attribute (e.g., on LLMError)
        if hasattr(exception, "retryable"):
            return bool(exception.retryable)

        return True


def with_retry(
    config: RetryConfig | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for async functions with retry logic."""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            attempt = 0
            last_exception: Exception | None = None

            async for attempt_info in AsyncRetrying(
                stop=stop_after_attempt(config.max_attempts),
                wait=wait_exponential(
                    multiplier=config.base_delay,
                    max=config.max_delay,
                ),
                retry=retry_if_exception(config.should_retry),
                reraise=True,
            ):
                with attempt_info:
                    attempt += 1
                    if attempt > 1:
                        logger.info(
                            "Retrying function",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=config.max_attempts,
                        )
                    return await func(*args, **kwargs)

            # This should never be reached due to reraise=True
            raise last_exception or RuntimeError("Unexpected retry exit")

        return wrapper

    return decorator


async def retry_async(
    func: Callable[[], Awaitable[T]],
    config: RetryConfig | None = None,
) -> T:
    """Execute an async function with retry logic."""
    if config is None:
        config = RetryConfig()

    attempt = 0

    try:
        async for attempt_info in AsyncRetrying(
            stop=stop_after_attempt(config.max_attempts),
            wait=wait_exponential(
                multiplier=config.base_delay,
                max=config.max_delay,
            ),
            retry=retry_if_exception(config.should_retry),
            reraise=True,
        ):
            with attempt_info:
                attempt += 1
                if attempt > 1:
                    logger.info(
                        "Retrying operation",
                        attempt=attempt,
                        max_attempts=config.max_attempts,
                    )
                return await func()
    except RetryError:
        raise

    raise RuntimeError("Unexpected retry exit")
