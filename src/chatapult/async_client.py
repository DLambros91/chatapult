import logging
from typing import Any, Dict, Optional, List

import httpx

from .exceptions import APIError, ConfigurationError, NetworkError
from .models import CardWithId

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
        self,
        text: Optional[str] = None,
        *,
        cards: Optional[List[CardWithId]] = None,
        thread_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sends an asynchronous message to the Google Chat Space."""
        if not text and not cards:
            raise ValueError(
                "You must provide either 'text' or 'cards' to send a message."
            )

        payload: Dict[str, Any] = {}

        if text:
            payload["text"] = text

        if cards:
            payload["cardsV2"] = [card.to_dict() for card in cards]

        if thread_name:
            payload["thread"] = {"name": thread_name}

        try:
            response = await self._client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(
                f"Google Chat API returned {e.response.status_code}: {e.response.text}",
                response=e.response,
            ) from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error while sending message: {e}") from e

    async def aclose(self) -> None:
        """Close the underlying asynchronous HTTP client connections."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncChatClient":
        """Enable usage as an asynchronous context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure connections are closed when exiting the context manager."""
        await self.aclose()
