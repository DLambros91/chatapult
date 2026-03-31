from typing import Any, Dict, Optional, List

import httpx

# Import our new custom exceptions
from .exceptions import APIError, ConfigurationError, NetworkError, RateLimitError
from .models import CardWithId

from .utils import retry_upon_rate_limit


class ChatClient:
    """A synchronous client for interacting with Google Chat Webhooks.

    This client uses httpx's Client to send messages in a blocking manner.
    """

    def __init__(
        self,
        webhook_url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_wait_min: float = 1.0,
        retry_wait_max: float = 60.0,
    ) -> None:
        """Initialize the ChatClient.

        Configures HTTP client and retry mechanism for sending
        messages to a Google Chat webhook.

        Attributes:
            webhook_url: The URL of the webhook to which
                requests will be sent.

        Args:
            webhook_url: The webhook URL as a string. Must be
                a valid and non-empty URL.
            timeout: Timeout for HTTP requests in seconds.
                Defaults to 10.0.
            max_retries: Maximum number of retries for failed
                requests. Defaults to 3.
            retry_wait_min: Minimum wait time between retries
                in seconds. Defaults to 1.0.
            retry_wait_max: Maximum wait time between retries
                in seconds. Defaults to 60.0.

        Raises:
            ConfigurationError: If an invalid or empty
                webhook_url is provided.
        """
        if not webhook_url:
            raise ConfigurationError("A valid webhook_url must be provided.")

        self.webhook_url = webhook_url
        self._client = httpx.Client(timeout=timeout)
        self._max_retries = max_retries
        self._retry_wait_min = retry_wait_min
        self._retry_wait_max = retry_wait_max

    def send_message(
        self,
        text: Optional[str] = None,
        *,
        cards: Optional[List[CardWithId]] = None,
        thread_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message to the Google Chat Space.

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

        @retry_upon_rate_limit(
            max_retries=self._max_retries,
            retry_wait_max=self._retry_wait_max,
            retry_wait_min=self._retry_wait_min,
        )
        def _do_post() -> Dict[str, Any]:
            try:
                response = self._client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitError(
                        f"Google Chat API rate limited (429): {e.response.text}",
                        response=e.response,
                    ) from e
                raise APIError(
                    f"Google Chat API returned "
                    f"{e.response.status_code}: "
                    f"{e.response.text}",
                    response=e.response,
                ) from e
            except httpx.RequestError as e:
                raise NetworkError(f"Network error while sending message: {e}") from e

        return _do_post()

    def close(self) -> None:
        """Close the underlying HTTP client connections."""
        self._client.close()

    def __enter__(self) -> "ChatClient":
        """Enable usage as a context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure connections are closed when exiting the context manager."""
        self.close()
