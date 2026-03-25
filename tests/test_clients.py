import httpx
import json
import pytest
from pytest_httpx import HTTPXMock

from chatapult.client import ChatClient
from chatapult.async_client import AsyncChatClient
from chatapult.exceptions import APIError, ConfigurationError, NetworkError

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


# ---------------------------------------------------------------------------
# Asynchronous Client Tests
# ---------------------------------------------------------------------------


def test_async_client_init_empty_url() -> None:
    """Ensure AsyncChatClient raises ConfigurationError if webhook is empty."""
    with pytest.raises(ConfigurationError):
        AsyncChatClient(webhook_url="")


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
