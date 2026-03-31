"""Custom exceptions for the Chatapult library.

This module defines a hierarchy of exceptions that can be raised by the Chatapult
clients.
"""

from typing import Optional

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
            # checking if headers are coming from google chat or not
            raw = response.headers.get("Retry-After")
            if raw is not None:
                try:
                    self.retry_after = float(raw)
                except ValueError:
                    self.retry_after = None
