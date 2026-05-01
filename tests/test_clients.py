import datetime
import httpx
import json
import pytest
from pytest_httpx import HTTPXMock

from chatapult.client import ChatClient
from chatapult.async_client import AsyncChatClient
from chatapult.exceptions import (
    APIError,
    ConfigurationError,
    NetworkError,
    RateLimitError,
    ServerError,
)
from chatapult.models import CardWithId, Card

# Dummy webhook URL for testing
WEBHOOK_URL = (
    "https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=KEY&token=TOKEN"
)


# ---------------------------------------------------------------------------
# Synchronous Client Tests
# ---------------------------------------------------------------------------


def test_sync_client_init_empty_url() -> None:
    """Ensure ChatClient raises ConfigurationError if webhook is empty."""
    with pytest.raises(ConfigurationError):
        ChatClient(webhook_url="")


def test_sync_client_init_negative_max_retries() -> None:
    """Ensure ChatClient raises ConfigurationError for negative max_retries."""
    with pytest.raises(ConfigurationError, match="max_retries"):
        ChatClient(WEBHOOK_URL, max_retries=-1)


def test_sync_client_init_negative_retry_wait_min() -> None:
    """Ensure ChatClient raises ConfigurationError for negative retry_wait_min."""
    with pytest.raises(ConfigurationError, match="retry_wait_min"):
        ChatClient(WEBHOOK_URL, retry_wait_min=-1.0)


def test_sync_client_init_retry_wait_max_less_than_min() -> None:
    """Ensure ChatClient raises ConfigurationError when max < min wait."""
    with pytest.raises(ConfigurationError, match="retry_wait_max"):
        ChatClient(WEBHOOK_URL, retry_wait_min=10.0, retry_wait_max=5.0)


def test_sync_send_message_success(httpx_mock: HTTPXMock) -> None:
    """Test sending a basic text message successfully."""
    mock_response = {"name": "spaces/SPACE/messages/MSG", "text": "Hello World!"}
    httpx_mock.add_response(json=mock_response, status_code=200)

    with ChatClient(WEBHOOK_URL) as client:
        response = client.send_message("Hello World!")

    assert response == mock_response

    # Verify the correct payload was sent by parsing the JSON
    request = httpx_mock.get_request()
    assert request is not None
    request_data = json.loads(request.read())
    assert request_data["text"] == "Hello World!"


def test_sync_send_message_with_thread(httpx_mock: HTTPXMock) -> None:
    """Test sending a message to a specific thread."""
    httpx_mock.add_response(json={}, status_code=200)
    thread_id = "spaces/SPACE_ID/threads/THREAD_ID"

    with ChatClient(WEBHOOK_URL) as client:
        client.send_message("Reply message", thread_name=thread_id)

    request = httpx_mock.get_request()
    assert request is not None

    # Verify thread payload is included by parsing the JSON
    request_data = json.loads(request.read())
    assert request_data["thread"]["name"] == "spaces/SPACE_ID/threads/THREAD_ID"


def test_sync_api_error(httpx_mock: HTTPXMock) -> None:
    """Test that HTTP errors are cleanly wrapped in our custom APIError."""
    httpx_mock.add_response(status_code=400, text="Bad Request")

    with ChatClient(WEBHOOK_URL) as client:
        with pytest.raises(APIError) as exc_info:
            client.send_message("This will fail")

    assert exc_info.value.status_code == 400
    assert "Bad Request" in str(exc_info.value)


def test_sync_network_error(httpx_mock: HTTPXMock) -> None:
    """Test that httpx connection errors are wrapped in our NetworkError."""
    httpx_mock.add_exception(httpx.ReadTimeout("Connection timed out"))

    with ChatClient(WEBHOOK_URL) as client:
        with pytest.raises(NetworkError) as exc_info:
            client.send_message("This will timeout")

    assert "Connection timed out" in str(exc_info.value)


def test_sync_send_message_with_cards(httpx_mock: HTTPXMock) -> None:
    """Test sending a message containing a V2 Card."""
    httpx_mock.add_response(json={}, status_code=200)

    card = CardWithId(cardId="test-card", card=Card())

    with ChatClient(WEBHOOK_URL) as client:
        client.send_message(cards=[card])

    request = httpx_mock.get_request()
    assert request is not None
    request_data = json.loads(request.read())

    assert "cardsV2" in request_data
    assert request_data["cardsV2"][0]["cardId"] == "test-card"


def test_sync_empty_message() -> None:
    """Test that sending a message without text or cards raises a ValueError."""
    with ChatClient(WEBHOOK_URL) as client:
        with pytest.raises(
            ValueError, match="You must provide either 'text' or 'cards'"
        ):
            client.send_message()


# ---------------------------------------------------------------------------
# Synchronous Client Retry Tests (429 Rate Limiting)
# ---------------------------------------------------------------------------


def test_sync_rate_limit_raises_rate_limit_error(httpx_mock: HTTPXMock) -> None:
    """Test that a 429 response raises RateLimitError, not generic APIError."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            client.send_message("This will be rate limited")

    assert exc_info.value.status_code == 429
    assert "429" in str(exc_info.value)
    assert "Too Many Requests" in str(exc_info.value)


def test_sync_rate_limit_is_api_error_subclass(httpx_mock: HTTPXMock) -> None:
    """Test that RateLimitError is catchable as APIError (subclass relationship)."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(APIError) as exc_info:
            client.send_message("This will be rate limited")

    assert isinstance(exc_info.value, RateLimitError)
    assert exc_info.value.status_code == 429


def test_sync_rate_limit_retry_succeeds(httpx_mock: HTTPXMock) -> None:
    """Test that a transient 429 followed by a 200 succeeds after retry."""
    # First request → 429, second request → 200
    httpx_mock.add_response(status_code=429, text="Too Many Requests")
    httpx_mock.add_response(
        status_code=200, json={"name": "spaces/SPACE/messages/MSG", "text": "OK"}
    )

    with ChatClient(
        WEBHOOK_URL, max_retries=1, retry_wait_min=0, retry_wait_max=0
    ) as client:
        response = client.send_message("Retry me")

    assert response == {"name": "spaces/SPACE/messages/MSG", "text": "OK"}

    # Verify two requests were made (original + 1 retry)
    requests = httpx_mock.get_requests()
    assert len(requests) == 2


def test_sync_rate_limit_multiple_retries_then_success(httpx_mock: HTTPXMock) -> None:
    """Test that multiple consecutive 429s are retried until success."""
    # Two 429s, then success
    httpx_mock.add_response(status_code=429, text="Too Many Requests")
    httpx_mock.add_response(status_code=429, text="Too Many Requests")
    httpx_mock.add_response(status_code=200, json={"text": "Finally!"})

    with ChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        response = client.send_message("Retry me twice")

    assert response == {"text": "Finally!"}

    # Verify three requests were made (original + 2 retries)
    requests = httpx_mock.get_requests()
    assert len(requests) == 3


def test_sync_rate_limit_retry_exhausted(httpx_mock: HTTPXMock) -> None:
    """Test that RateLimitError is raised after all retries are exhausted."""
    # All attempts return 429
    httpx_mock.add_response(status_code=429, text="Too Many Requests")
    httpx_mock.add_response(status_code=429, text="Still Too Many")
    httpx_mock.add_response(status_code=429, text="Still Too Many")

    with ChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            client.send_message("This will exhaust retries")

    assert exc_info.value.status_code == 429

    # Verify all attempts were made (original + 2 retries)
    requests = httpx_mock.get_requests()
    assert len(requests) == 3


def test_sync_rate_limit_retry_after_header(httpx_mock: HTTPXMock) -> None:
    """Test that the Retry-After header value is parsed into RateLimitError."""
    httpx_mock.add_response(
        status_code=429,
        text="Too Many Requests",
        headers={"Retry-After": "5"},
    )

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            client.send_message("Check retry-after")

    assert exc_info.value.retry_after == 5.0
    assert exc_info.value.status_code == 429


def test_sync_rate_limit_retry_after_header_missing(httpx_mock: HTTPXMock) -> None:
    """Test that retry_after is None when Retry-After header is absent."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            client.send_message("No retry-after header")

    assert exc_info.value.retry_after is None


def test_sync_rate_limit_retry_after_negative_clamped(httpx_mock: HTTPXMock) -> None:
    """Test that a negative delay-seconds value is clamped to 0."""
    httpx_mock.add_response(
        status_code=429,
        text="Too Many Requests",
        headers={"Retry-After": "-10"},
    )

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            client.send_message("Negative retry-after")

    assert exc_info.value.retry_after == 0.0


def test_sync_rate_limit_retry_after_http_date(httpx_mock: HTTPXMock) -> None:
    """Test that an HTTP-date Retry-After value is parsed to a non-negative delay."""
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        seconds=30
    )
    http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
    httpx_mock.add_response(
        status_code=429,
        text="Too Many Requests",
        headers={"Retry-After": http_date},
    )

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            client.send_message("HTTP-date retry-after")

    assert exc_info.value.retry_after is not None
    assert exc_info.value.retry_after >= 0.0


def test_sync_rate_limit_retry_after_unparseable(httpx_mock: HTTPXMock) -> None:
    """Test that an unparseable Retry-After value results in retry_after=None."""
    httpx_mock.add_response(
        status_code=429,
        text="Too Many Requests",
        headers={"Retry-After": "not-a-valid-value"},
    )

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            client.send_message("Unparseable retry-after")

    assert exc_info.value.retry_after is None


def test_sync_non_429_error_not_retried(httpx_mock: HTTPXMock) -> None:
    """Test that non-retryable errors (e.g. 400) are NOT retried."""
    httpx_mock.add_response(status_code=400, text="Bad Request")

    with ChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(APIError) as exc_info:
            client.send_message("This is a bad request")

    # Should NOT be a RateLimitError
    assert not isinstance(exc_info.value, RateLimitError)
    assert exc_info.value.status_code == 400

    # Only one request — no retries for 4xx errors
    requests = httpx_mock.get_requests()
    assert len(requests) == 1


# ---------------------------------------------------------------------------
# Synchronous Client Retry Tests (5xx Server Errors)
# ---------------------------------------------------------------------------


def test_sync_server_error_raises_server_error(httpx_mock: HTTPXMock) -> None:
    """Test that a 500 response raises ServerError, not generic APIError."""
    httpx_mock.add_response(status_code=500, text="Internal Server Error")

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(ServerError) as exc_info:
            client.send_message("This will fail with 500")

    assert exc_info.value.status_code == 500
    assert "500" in str(exc_info.value)
    assert "Internal Server Error" in str(exc_info.value)


def test_sync_server_error_is_api_error_subclass(httpx_mock: HTTPXMock) -> None:
    """Test that ServerError is catchable as APIError (subclass relationship)."""
    httpx_mock.add_response(status_code=503, text="Service Unavailable")

    with ChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(APIError) as exc_info:
            client.send_message("This will fail with 503")

    assert isinstance(exc_info.value, ServerError)
    assert exc_info.value.status_code == 503


def test_sync_server_error_retry_succeeds(httpx_mock: HTTPXMock) -> None:
    """Test that a transient 500 followed by a 200 succeeds after retry."""
    httpx_mock.add_response(status_code=500, text="Internal Server Error")
    httpx_mock.add_response(
        status_code=200, json={"name": "spaces/SPACE/messages/MSG", "text": "OK"}
    )

    with ChatClient(
        WEBHOOK_URL, max_retries=1, retry_wait_min=0, retry_wait_max=0
    ) as client:
        response = client.send_message("Retry me")

    assert response == {"name": "spaces/SPACE/messages/MSG", "text": "OK"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 2


def test_sync_server_error_multiple_retries_then_success(httpx_mock: HTTPXMock) -> None:
    """Test that multiple consecutive 5xx responses are retried until success."""
    httpx_mock.add_response(status_code=502, text="Bad Gateway")
    httpx_mock.add_response(status_code=503, text="Service Unavailable")
    httpx_mock.add_response(status_code=200, json={"text": "Finally!"})

    with ChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        response = client.send_message("Retry me twice")

    assert response == {"text": "Finally!"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 3


def test_sync_server_error_retry_exhausted(httpx_mock: HTTPXMock) -> None:
    """Test that ServerError is raised after all retries are exhausted."""
    httpx_mock.add_response(status_code=500, text="Internal Server Error")
    httpx_mock.add_response(status_code=500, text="Internal Server Error")
    httpx_mock.add_response(status_code=500, text="Internal Server Error")

    with ChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(ServerError) as exc_info:
            client.send_message("This will exhaust retries")

    assert exc_info.value.status_code == 500

    requests = httpx_mock.get_requests()
    assert len(requests) == 3


def test_sync_4xx_not_retried_but_5xx_is(httpx_mock: HTTPXMock) -> None:
    """Test that 4xx errors (except 429) are not retried while 5xx would be."""
    httpx_mock.add_response(status_code=403, text="Forbidden")

    with ChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(APIError) as exc_info:
            client.send_message("Forbidden request")

    assert not isinstance(exc_info.value, ServerError)
    assert exc_info.value.status_code == 403

    requests = httpx_mock.get_requests()
    assert len(requests) == 1


# ---------------------------------------------------------------------------
# Asynchronous Client Tests
# ---------------------------------------------------------------------------


def test_async_client_init_empty_url() -> None:
    """Ensure AsyncChatClient raises ConfigurationError if webhook is empty."""
    with pytest.raises(ConfigurationError):
        AsyncChatClient(webhook_url="")


def test_async_client_init_negative_max_retries() -> None:
    """Ensure AsyncChatClient raises ConfigurationError for negative max_retries."""
    with pytest.raises(ConfigurationError, match="max_retries"):
        AsyncChatClient(WEBHOOK_URL, max_retries=-1)


def test_async_client_init_negative_retry_wait_min() -> None:
    """Ensure AsyncChatClient raises ConfigurationError for negative retry_wait_min."""
    with pytest.raises(ConfigurationError, match="retry_wait_min"):
        AsyncChatClient(WEBHOOK_URL, retry_wait_min=-1.0)


def test_async_client_init_retry_wait_max_less_than_min() -> None:
    """Ensure AsyncChatClient raises ConfigurationError when max < min wait."""
    with pytest.raises(ConfigurationError, match="retry_wait_max"):
        AsyncChatClient(WEBHOOK_URL, retry_wait_min=10.0, retry_wait_max=5.0)


@pytest.mark.asyncio
async def test_async_send_message_with_thread(httpx_mock: HTTPXMock) -> None:
    """Test sending a message to a specific thread (async)."""
    httpx_mock.add_response(json={}, status_code=200)
    thread_id = "spaces/SPACE_ID/threads/THREAD_ID"

    async with AsyncChatClient(WEBHOOK_URL) as client:
        await client.send_message("Async reply message", thread_name=thread_id)

    request = httpx_mock.get_request()
    assert request is not None

    # Verify thread payload is included by parsing the JSON
    request_data = json.loads(request.read())
    assert request_data["thread"]["name"] == thread_id


@pytest.mark.asyncio
async def test_async_send_message_success(httpx_mock: HTTPXMock) -> None:
    """Test sending a basic text message successfully (async)."""
    mock_response = {"name": "spaces/SPACE/messages/MSG", "text": "Async Hello!"}
    httpx_mock.add_response(json=mock_response, status_code=200)

    async with AsyncChatClient(WEBHOOK_URL) as client:
        response = await client.send_message("Async Hello!")

    assert response == mock_response


@pytest.mark.asyncio
async def test_async_api_error(httpx_mock: HTTPXMock) -> None:
    """Test that HTTP errors are cleanly wrapped in our custom APIError (async)."""
    httpx_mock.add_response(status_code=404, text="Space not found")

    async with AsyncChatClient(WEBHOOK_URL) as client:
        with pytest.raises(APIError) as exc_info:
            await client.send_message("This will fail")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_async_network_error(httpx_mock: HTTPXMock) -> None:
    """Test that network errors are wrapped in our NetworkError (async)."""
    httpx_mock.add_exception(httpx.ConnectError("Network unreachable"))

    async with AsyncChatClient(WEBHOOK_URL) as client:
        with pytest.raises(NetworkError):
            await client.send_message("This will fail")


@pytest.mark.asyncio
async def test_async_send_message_with_cards(httpx_mock: HTTPXMock) -> None:
    """Test sending an async message containing a V2 Card."""
    httpx_mock.add_response(json={}, status_code=200)

    card = CardWithId(cardId="test-card", card=Card())

    async with AsyncChatClient(WEBHOOK_URL) as client:
        await client.send_message(cards=[card])

    request = httpx_mock.get_request()
    assert request is not None
    request_data = json.loads(request.read())

    assert "cardsV2" in request_data
    assert request_data["cardsV2"][0]["cardId"] == "test-card"


@pytest.mark.asyncio
async def test_async_empty_message() -> None:
    """Test that sending an async message without text or cards raises a ValueError."""
    async with AsyncChatClient(WEBHOOK_URL) as client:
        with pytest.raises(
            ValueError, match="You must provide either 'text' or 'cards'"
        ):
            await client.send_message()


# ---------------------------------------------------------------------------
# Asynchronous Client Retry Tests (429 Rate Limiting)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_rate_limit_raises_rate_limit_error(httpx_mock: HTTPXMock) -> None:
    """Test that a 429 response raises RateLimitError (async)."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.send_message("This will be rate limited")

    assert exc_info.value.status_code == 429
    assert "429" in str(exc_info.value)
    assert "Too Many Requests" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_rate_limit_is_api_error_subclass(httpx_mock: HTTPXMock) -> None:
    """Test that RateLimitError is catchable as APIError (async)."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(APIError) as exc_info:
            await client.send_message("This will be rate limited")

    assert isinstance(exc_info.value, RateLimitError)
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_async_rate_limit_retry_succeeds(httpx_mock: HTTPXMock) -> None:
    """Test that a transient 429 followed by a 200 succeeds after retry (async)."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")
    httpx_mock.add_response(
        status_code=200, json={"name": "spaces/SPACE/messages/MSG", "text": "OK"}
    )

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=1, retry_wait_min=0, retry_wait_max=0
    ) as client:
        response = await client.send_message("Retry me")

    assert response == {"name": "spaces/SPACE/messages/MSG", "text": "OK"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_async_rate_limit_multiple_retries_then_success(
    httpx_mock: HTTPXMock,
) -> None:
    """Test that multiple consecutive 429s are retried until success (async)."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")
    httpx_mock.add_response(status_code=429, text="Too Many Requests")
    httpx_mock.add_response(status_code=200, json={"text": "Finally!"})

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        response = await client.send_message("Retry me twice")

    assert response == {"text": "Finally!"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 3


@pytest.mark.asyncio
async def test_async_rate_limit_retry_exhausted(httpx_mock: HTTPXMock) -> None:
    """Test that RateLimitError is raised after all retries are exhausted (async)."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")
    httpx_mock.add_response(status_code=429, text="Still Too Many")
    httpx_mock.add_response(status_code=429, text="Still Too Many")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.send_message("This will exhaust retries")

    assert exc_info.value.status_code == 429

    requests = httpx_mock.get_requests()
    assert len(requests) == 3


@pytest.mark.asyncio
async def test_async_rate_limit_retry_after_header(httpx_mock: HTTPXMock) -> None:
    """Test that the Retry-After header value is parsed into RateLimitError (async)."""
    httpx_mock.add_response(
        status_code=429,
        text="Too Many Requests",
        headers={"Retry-After": "5"},
    )

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.send_message("Check retry-after")

    assert exc_info.value.retry_after == 5.0
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_async_rate_limit_retry_after_header_missing(
    httpx_mock: HTTPXMock,
) -> None:
    """Test that retry_after is None when Retry-After header is absent (async)."""
    httpx_mock.add_response(status_code=429, text="Too Many Requests")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.send_message("No retry-after header")

    assert exc_info.value.retry_after is None


@pytest.mark.asyncio
async def test_async_rate_limit_retry_after_negative_clamped(
    httpx_mock: HTTPXMock,
) -> None:
    """Test that a negative delay-seconds value is clamped to 0 (async)."""
    httpx_mock.add_response(
        status_code=429,
        text="Too Many Requests",
        headers={"Retry-After": "-10"},
    )

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.send_message("Negative retry-after")

    assert exc_info.value.retry_after == 0.0


@pytest.mark.asyncio
async def test_async_rate_limit_retry_after_http_date(httpx_mock: HTTPXMock) -> None:
    """Test that HTTP-date Retry-After is parsed to a non-negative delay (async)."""
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        seconds=30
    )
    http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
    httpx_mock.add_response(
        status_code=429,
        text="Too Many Requests",
        headers={"Retry-After": http_date},
    )

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.send_message("HTTP-date retry-after")

    assert exc_info.value.retry_after is not None
    assert exc_info.value.retry_after >= 0.0


@pytest.mark.asyncio
async def test_async_rate_limit_retry_after_unparseable(httpx_mock: HTTPXMock) -> None:
    """Test that an unparseable Retry-After results in retry_after=None (async)."""
    httpx_mock.add_response(
        status_code=429,
        text="Too Many Requests",
        headers={"Retry-After": "not-a-valid-value"},
    )

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(RateLimitError) as exc_info:
            await client.send_message("Unparseable retry-after")

    assert exc_info.value.retry_after is None


@pytest.mark.asyncio
async def test_async_non_429_error_not_retried(httpx_mock: HTTPXMock) -> None:
    """Test that non-retryable errors (e.g. 400) are NOT retried (async)."""
    httpx_mock.add_response(status_code=400, text="Bad Request")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(APIError) as exc_info:
            await client.send_message("This is a bad request")

    assert not isinstance(exc_info.value, RateLimitError)
    assert exc_info.value.status_code == 400

    requests = httpx_mock.get_requests()
    assert len(requests) == 1


# ---------------------------------------------------------------------------
# Asynchronous Client Retry Tests (5xx Server Errors)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_server_error_raises_server_error(httpx_mock: HTTPXMock) -> None:
    """Test that a 500 response raises ServerError, not generic APIError (async)."""
    httpx_mock.add_response(status_code=500, text="Internal Server Error")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(ServerError) as exc_info:
            await client.send_message("This will fail with 500")

    assert exc_info.value.status_code == 500
    assert "500" in str(exc_info.value)
    assert "Internal Server Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_server_error_is_api_error_subclass(httpx_mock: HTTPXMock) -> None:
    """Test that ServerError is catchable as APIError (async)."""
    httpx_mock.add_response(status_code=503, text="Service Unavailable")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=0, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(APIError) as exc_info:
            await client.send_message("This will fail with 503")

    assert isinstance(exc_info.value, ServerError)
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_async_server_error_retry_succeeds(httpx_mock: HTTPXMock) -> None:
    """Test that a transient 500 followed by a 200 succeeds after retry (async)."""
    httpx_mock.add_response(status_code=500, text="Internal Server Error")
    httpx_mock.add_response(
        status_code=200, json={"name": "spaces/SPACE/messages/MSG", "text": "OK"}
    )

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=1, retry_wait_min=0, retry_wait_max=0
    ) as client:
        response = await client.send_message("Retry me")

    assert response == {"name": "spaces/SPACE/messages/MSG", "text": "OK"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_async_server_error_multiple_retries_then_success(
    httpx_mock: HTTPXMock,
) -> None:
    """Test that multiple 5xx responses are retried until success (async)."""
    httpx_mock.add_response(status_code=502, text="Bad Gateway")
    httpx_mock.add_response(status_code=503, text="Service Unavailable")
    httpx_mock.add_response(status_code=200, json={"text": "Finally!"})

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        response = await client.send_message("Retry me twice")

    assert response == {"text": "Finally!"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 3


@pytest.mark.asyncio
async def test_async_server_error_retry_exhausted(httpx_mock: HTTPXMock) -> None:
    """Test that ServerError is raised after all retries are exhausted (async)."""
    httpx_mock.add_response(status_code=500, text="Internal Server Error")
    httpx_mock.add_response(status_code=500, text="Internal Server Error")
    httpx_mock.add_response(status_code=500, text="Internal Server Error")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(ServerError) as exc_info:
            await client.send_message("This will exhaust retries")

    assert exc_info.value.status_code == 500

    requests = httpx_mock.get_requests()
    assert len(requests) == 3


@pytest.mark.asyncio
async def test_async_4xx_not_retried_but_5xx_is(httpx_mock: HTTPXMock) -> None:
    """Test that 4xx errors (except 429) are not retried while 5xx would be (async)."""
    httpx_mock.add_response(status_code=403, text="Forbidden")

    async with AsyncChatClient(
        WEBHOOK_URL, max_retries=2, retry_wait_min=0, retry_wait_max=0
    ) as client:
        with pytest.raises(APIError) as exc_info:
            await client.send_message("Forbidden request")

    assert not isinstance(exc_info.value, ServerError)
    assert exc_info.value.status_code == 403

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
