import logging
from typing import Any, Dict, Optional, List

import httpx

# Import our new custom exceptions
from .exceptions import APIError, ConfigurationError, NetworkError
from .models import CardWithId

logger = logging.getLogger(__name__)


class ChatClient:
    """A synchronous client for interacting with Google Chat Webhooks.

    This client uses httpx's Client to send messages in a blocking manner.
    """

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        """Initialize the ChatClient.

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
        self,
        text: Optional[str] = None,
        *,
        cards: Optional[List[CardWithId]] = None,
        thread_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sends a message to the Google Chat Space.

        Args:
            text: The plain text message to send.
            cards: A list of rich V2 Cards to send.
            thread_name: The resource name of the thread to reply to.
        """
        if not text and not cards:
            raise ValueError(
                "You must provide either 'text' or 'cards' to send a message."
            )

        payload: Dict[str, Any] = {}

        if text:
            payload["text"] = text

        if cards:
            # Convert our dataclasses into clean dictionaries
            payload["cardsV2"] = [card.to_dict() for card in cards]

        if thread_name:
            payload["thread"] = {"name": thread_name}

        try:
            response = self._client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(
                f"Google Chat API returned {e.response.status_code}: {e.response.text}",
                response=e.response,
            ) from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error while sending message: {e}") from e

    def close(self) -> None:
        """Close the underlying HTTP client connections."""
        self._client.close()

    def __enter__(self) -> "ChatClient":
        """Enable usage as a context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure connections are closed when exiting the context manager."""
        self.close()
