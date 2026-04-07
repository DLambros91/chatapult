![Chatapult Banner](https://raw.githubusercontent.com/DLambros91/chatapult/refs/heads/main/images/banner.png)

# Chatapult

A fast, Pythonic API wrapper for Google Chat webhooks.

Chatapult is designed to make sending automated notifications, CI/CD alerts, and rich UI cards to Google Workspace Spaces effortless. Whether you need a simple synchronous alert or a high-throughput async notification integration, Chatapult handles the boilerplate so you can focus on your application.

[![PyPI Version](https://img.shields.io/pypi/v/chatapult.svg)](https://pypi.org/project/chatapult/)
[![Python Versions](https://img.shields.io/pypi/pyversions/chatapult.svg)](https://pypi.org/project/chatapult/)
[![codecov](https://codecov.io/gh/DLambros91/chatapult/graph/badge.svg?token=A5ZYCGQDGC)](https://codecov.io/gh/DLambros91/chatapult)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://raw.githubusercontent.com/DLambros91/chatapult/refs/heads/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

* **Zero Boilerplate:** Send a message to a Google Chat Space in three lines of code.
* **Async Ready:** First-class support for `asyncio`, making it perfect for FastAPI, Discord bots, and high-concurrency event loops.
* **Rich V2 Cards:** Construct complex Google Chat Cards and Widgets using clean Python objects instead of nested JSON.
* **Threaded Replies:** Easily group related alerts by replying to specific message threads.
* **Fully Typed:** Built with standard Python type hints for excellent IDE autocomplete and static checking.

## Installation

Install via pip:

```bash
pip install chatapult
```

## Quick Start

**Security Note:** Never hardcode your webhook URLs. Always load them securely from environment variables or a secrets manager.

### Synchronous Usage

Perfect for simple scripts, cron jobs, or basic data pipelines.

```python
import os
from chatapult import ChatClient, APIError

webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL")

try:
    with ChatClient(webhook_url) as client:
        response = client.send_message("Hello from Chatapult!")
        print("Message sent successfully!")
except APIError as e:
    print(f"Failed to send message: {e}")
```

![Sync Message](https://raw.githubusercontent.com/DLambros91/chatapult/refs/heads/main/images/example_sync_message.png)

### Mentioning Users

Chatapult provides helper functions for Google Chat user mentions.
```python
import os
from chatapult import ChatClient
from chatapult.formatters import mention_all, mention_user

webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL")

# Mention everyone in the space
text = f"{mention_all()} Heads up, deployment is starting!"

# Mention a specific user by ID
text = f"Please review this PR from {mention_user('12345')}."

with ChatClient(webhook_url) as client:
    client.send_message(text)
```

### Asynchronous Usage

Ideal for web servers, async task queues, or applications where you cannot block the main thread.

```python
import asyncio
import os
from chatapult import AsyncChatClient, NetworkError

async def main():
    webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL")

    try:
        async with AsyncChatClient(webhook_url) as client:
            await client.send_message("Hello from the async event loop!")
            print("Async message sent successfully!")
    except NetworkError as e:
        print(f"Network issue encountered: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

![Async Message](https://raw.githubusercontent.com/DLambros91/chatapult/refs/heads/main/images/example_async_message.png)

### Advanced Usage: Sending Rich V2 Cards

Google Chat's raw JSON for V2 Cards is heavily nested and prone to typos. Chatapult provides clean, typed dataclasses so you can build complex UI cards using standard Python objects.

```python
import os
from chatapult import ChatClient
from chatapult.models import (
    CardWithId, Card, CardHeader, Section, Widget, TextParagraph
)

webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL")

# 1. Build your Card using Python dataclasses
alert_card = CardWithId(
    cardId="server-alert-123",
    card=Card(
        header=CardHeader(
            title="Production Alert 🚨",
            subtitle="Database CPU Spiking",
            imageUrl="https://example.com/alert-icon.png"
        ),
        sections=[
            Section(
                header="System Metrics",
                widgets=[
                    Widget(
                        textParagraph=TextParagraph(
                            text="<b>Primary DB</b> CPU utilization is at 98%."
                        )
                    )
                ]
            )
        ]
    )
)

# 2. Send the card!
with ChatClient(webhook_url) as client:
    client.send_message(cards=[alert_card])
    print("Rich card sent successfully!")
```

Or simply with

```python
import os
from chatapult import ChatClient
from chatapult.models import CardWithId

webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL")

alert_card = CardWithId.create_simple(
    card_id="server-alert-1",
    title="Production Alert 🚨",
    subtitle="Database CPU Spiking",
    text="<b>Primary DB</b> CPU utilization is at 98%."
)

with ChatClient(webhook_url) as client:
    client.send_message(cards=[alert_card])
```

![Card Message](https://raw.githubusercontent.com/DLambros91/chatapult/refs/heads/main/images/example_card_message.png)

## Contributing
Contributions are welcome! If you'd like to help improve Chatapult, please review our [Contributing Guidelines](https://raw.githubusercontent.com/DLambros91/chatapult/refs/heads/main/CONTRIBUTING.md) and open an issue or pull request.

## License

This project is licensed under the MIT License - see [LICENSE](https://raw.githubusercontent.com/DLambros91/chatapult/refs/heads/main/LICENSE) for details.
