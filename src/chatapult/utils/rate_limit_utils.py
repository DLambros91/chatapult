from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    RetryCallState,
)

from chatapult.exceptions import RateLimitError, ServerError


def retry_upon_rate_limit(
    max_retries: int, retry_wait_min: float, retry_wait_max: float
):
    """Create a retry decorator for rate limit errors.

    Retries execution of a callable upon encountering a
    RateLimitError, using exponential backoff with configurable
    parameters. If the raised error provides a ``retry_after``
    duration, that value is used as the wait time instead.

    Args:
        max_retries (int): The maximum number of retry
            attempts allowed. Must be a positive integer.
        retry_wait_min (float): The minimum wait time
            (in seconds) between retry attempts. Must be
            a non-negative floating-point value.
        retry_wait_max (float): The maximum wait time
            (in seconds) between retry attempts. Must be
            greater than or equal to ``retry_wait_min``.

    Returns:
        Callable: A configured retry object that wraps a
        callable for retrying on rate limit errors.

    Raises:
        The original exception will be re-raised if all
        retry attempts are exhausted.
    """

    def _wait_with_rate_limit(retry_state: RetryCallState) -> float:
        """Wait function with rate limit error handling.

        Determines the wait time before retrying a call. If
        the outcome contains a RateLimitError with a
        ``retry_after`` value, that value is used. Otherwise,
        exponential backoff is applied using the configured
        minimum and maximum wait durations.

        Args:
            retry_state (RetryCallState): The state of
                the retry, including the outcome of the
                previous attempt.

        Returns:
            float: Seconds to wait before the next retry.
        """
        if retry_state.outcome is not None:
            exception_caught = retry_state.outcome.exception()
            if (
                isinstance(exception_caught, RateLimitError)
                and exception_caught.retry_after is not None
            ):
                return exception_caught.retry_after

        return wait_exponential(min=retry_wait_min, max=retry_wait_max)(retry_state)

    return retry(
        retry=retry_if_exception_type((RateLimitError, ServerError)),
        wait=_wait_with_rate_limit,
        stop=stop_after_attempt(max_retries + 1),
        reraise=True,
    )
