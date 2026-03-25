"""
Custom exceptions for the Chatapult library.
"""


class ChatapultError(Exception):
    """
    Base exception class for all Chatapult errors.
    All other custom exceptions in this library inherit from this base class,
    allowing users to catch any Chatapult-related error with a single except block.
    """

    pass


class ConfigurationError(ChatapultError):
    """
    Raised when there is a configuration issue, such as an empty or invalid webhook URL.
    """

    pass


class APIError(ChatapultError):
    """
    Raised when the Google Chat API returns an HTTP error response (e.g., 400 or 404).
    """

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class NetworkError(ChatapultError):
    """
    Raised when a network connection fails, times out, or the host is unreachable.
    """

    pass
