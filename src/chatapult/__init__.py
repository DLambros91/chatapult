"""
Chatapult: A fast, Pythonic API wrapper for Google Chat webhooks.
"""

# Explicitly define the version so developers can check it programmatically
__version__ = "0.1.0"

# Import the core components to expose them at the top level of the package
from .client import ChatClient
from .async_client import AsyncChatClient
from .exceptions import (
    APIError,
    ChatapultError,
    ConfigurationError,
    NetworkError,
)

# The __all__ list strictly defines the public API of your module.
# It tells IDEs and linters exactly what is safe for end-users to import,
# and hides internal modules (like 'logging' or 'httpx') from autocomplete.
__all__ = [
    "APIError",
    "AsyncChatClient",
    "ChatClient",
    "ChatapultError",
    "ConfigurationError",
    "NetworkError",
]
