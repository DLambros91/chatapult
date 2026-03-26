import logging
from typing import Any, Dict, Optional

import httpx

# Import our new custom exceptions
from .exceptions import APIError, ConfigurationError, NetworkError

logger = logging.getLogger(__name__)


class ChatClient:
    """
    A synchronous client for interacting with Google Chat Webhooks.
    """

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        """
        Initialize the ChatClient.

        Args:
            webhook_url (str): The full Google Chat webhook URL.
            timeout (float): Connection timeout in seconds. Defaults to 10.0.

        Raises:
            ConfigurationError: If the webhook_url is empty or invalid.
        """
        if not webhook_url:
            raise ConfigurationError("A valid webhook_url must be provided.")

        self.webhook_url = webhook_url
        self._client = httpx.Client(timeout=timeout)

    def send_message(
        self, text: str, thread_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a simple text message to the configured Google Chat Space.

        Args:
            text (str): The markdown-formatted text to send.
            thread_name (Optional[str]): The ID of an existing thread to reply to
                                         (e.g., 'spaces/SPACE_ID/threads/THREAD_ID').

        Returns:
            Dict[str, Any]: The JSON response from the Google Chat API representing the message.

        Raises:
            APIError: If the Google API returns a non-200 status code.
            NetworkError: If the network connection times out or fails.
        """
        payload: Dict[str, Any] = {"text": text}

        if thread_name:
            payload["thread"] = {"name": thread_name}

        try:
            response = self._client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Google Chat API error: {e.response.status_code} - {e.response.text}"
            )
            raise APIError(
                message=f"API request failed: {e.response.text}",
                status_code=e.response.status_code,
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Network error while connecting to Google Chat: {e}")
            raise NetworkError(f"Network request failed: {str(e)}") from e

    def close(self) -> None:
        """Close the underlying HTTP client connections."""
        self._client.close()

    def __enter__(self) -> "ChatClient":
        """Enable usage as a context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure connections are closed when exiting the context manager."""
        self.close()
