import logging
from typing import Any, Dict, Optional

import httpx

from .exceptions import APIError, ConfigurationError, NetworkError

logger = logging.getLogger(__name__)


class AsyncChatClient:
    """
    An asynchronous client for interacting with Google Chat Webhooks.
    """

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        """
        Initialize the AsyncChatClient.

        Args:
            webhook_url (str): The full Google Chat webhook URL.
            timeout (float): Connection timeout in seconds. Defaults to 10.0.

        Raises:
            ConfigurationError: If the webhook_url is empty.
        """
        if not webhook_url:
            raise ConfigurationError("A valid webhook_url must be provided.")

        self.webhook_url = webhook_url
        self._client = httpx.AsyncClient(timeout=timeout)

    async def send_message(
        self, text: str, thread_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously send a simple text message to the Google Chat Space.

        Args:
            text (str): The markdown-formatted text to send.
            thread_name (Optional[str]): The ID of an existing thread to reply to.

        Returns:
            Dict[str, Any]: The JSON response from the Google Chat API.

        Raises:
            APIError: If the Google API returns a non-200 status code.
            NetworkError: If the connection times out or fails.
        """
        payload: Dict[str, Any] = {"text": text}

        if thread_name:
            payload["thread"] = {"name": thread_name}

        try:
            response = await self._client.post(self.webhook_url, json=payload)
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

    async def aclose(self) -> None:
        """Close the underlying asynchronous HTTP client connections."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncChatClient":
        """Enable usage as an asynchronous context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure connections are closed when exiting the context manager."""
        await self.aclose()
