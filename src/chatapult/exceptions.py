"""
Custom exceptions for the Chatapult library.
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
        super().__init__(message)
        self.response = response
        self.status_code = response.status_code if response is not None else None
