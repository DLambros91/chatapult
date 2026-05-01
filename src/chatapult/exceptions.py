"""Custom exceptions for the Chatapult library.

This module defines a hierarchy of exceptions that can be raised by the Chatapult
clients.
"""

from email.utils import parsedate_to_datetime
from typing import Optional
import datetime

import httpx


class ChatapultError(Exception):
    """Base exception for all Chatapult errors."""

    pass


class ConfigurationError(ChatapultError):
    """Raised when the client is configured incorrectly."""

    pass


class NetworkError(ChatapultError):
    """Raised when a network request fails completely."""

    pass


class APIError(ChatapultError):
    """Raised when the Google Chat API returns an error HTTP status."""

    def __init__(self, message: str, response: Optional[httpx.Response] = None) -> None:
        """Initialize the APIError.

        Args:
            message: A human-readable error message.
            response: The original httpx.Response object that caused the error, if
                      available.
        """
        super().__init__(message)
        self.response = response
        self.status_code = response.status_code if response is not None else None


def _parse_retry_after(value: str) -> Optional[float]:
    """Parse a Retry-After header value into a non-negative delay in seconds.

    Supports both the delay-seconds form (e.g. ``"30"``) and the HTTP-date
    form (e.g. ``"Thu, 01 Jan 2026 00:00:00 GMT"``).  Negative delay-seconds
    values are clamped to 0.  Returns ``None`` when the value cannot be
    parsed.

    Args:
        value: The stripped Retry-After header string.

    Returns:
        Seconds to wait as a non-negative float, or ``None`` if unparseable.
    """
    # Try delay-seconds form first.
    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    # Try HTTP-date form (RFC 7231).
    try:
        retry_date = parsedate_to_datetime(value)
        now = datetime.datetime.now(datetime.timezone.utc)
        return max(0.0, (retry_date - now).total_seconds())
    except Exception:
        return None


class RateLimitError(APIError):
    """Raised when the Google Chat API returns a 429 Too Many Requests status."""

    def __init__(self, message: str, response: Optional[httpx.Response] = None) -> None:
        """Initialize the RateLimitError.

        Includes optional retry delay information based on
        a response.

        Attributes:
            retry_after: The number of seconds to wait before
                retrying if provided by the response.

        Args:
            message: The error message for the exception.
            response: An optional HTTP response object
                associated with this exception.
        """
        super().__init__(message, response=response)
        self.retry_after: Optional[float] = None
        if response is not None:
            raw = response.headers.get("Retry-After")
            if raw is not None:
                self.retry_after = _parse_retry_after(raw.strip())


class ServerError(APIError):
    """Raised when the API returns a 5xx server error status."""

    pass
