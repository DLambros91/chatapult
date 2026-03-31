from typing import Any, Dict, Optional, List

import httpx

from .exceptions import APIError, ConfigurationError, NetworkError, RateLimitError
from .models import CardWithId

from .utils import retry_upon_rate_limit


class AsyncChatClient:
    """An asynchronous client for interacting with Google Chat Webhooks.

    This client uses httpx's AsyncClient to send messages without blocking the event
    loop.
    """

    def __init__(
        self,
        webhook_url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_wait_min: float = 1.0,
        retry_wait_max: float = 60.0,
    ) -> None:
        """Initialize the AsyncChatClient.

        Configures an HTTP client and retry mechanism for
        sending messages to a Google Chat webhook.

        Args:
            webhook_url: The URL of the webhook to interact with.
            timeout: Timeout for HTTP requests in seconds.
                Defaults to 10.0.
            max_retries: Maximum number of retry attempts.
                Defaults to 3.
            retry_wait_min: Minimum wait between retries in
                seconds. Defaults to 1.0.
            retry_wait_max: Maximum wait between retries in
                seconds. Defaults to 60.0.

        Raises:
            ConfigurationError: If the provided webhook_url is
                invalid or not provided.
        """
        if not webhook_url:
            raise ConfigurationError("A valid webhook_url must be provided.")

        self.webhook_url = webhook_url
        self._client = httpx.AsyncClient(timeout=timeout)
        self._max_retries = max_retries
        self._retry_wait_min = retry_wait_min
        self._retry_wait_max = retry_wait_max

    async def send_message(
        self,
        text: Optional[str] = None,
        *,
        cards: Optional[List[CardWithId]] = None,
        thread_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an asynchronous message to the Google Chat Space."""
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

        @retry_upon_rate_limit(
            max_retries=self._max_retries,
            retry_wait_max=self._retry_wait_max,
            retry_wait_min=self._retry_wait_min,
        )
        async def do_async_post() -> Dict[str, Any]:
            try:
                response = await self._client.post(self.webhook_url, json=payload)
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

        return await do_async_post()

    async def aclose(self) -> None:
        """Close the underlying asynchronous HTTP client connections."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncChatClient":
        """Enable usage as an asynchronous context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure connections are closed when exiting the context manager."""
        await self.aclose()
