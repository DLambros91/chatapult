"""
Tests for the V2 Card dataclass models.
"""

from chatapult.models import (
    CardWithId,
    Card,
    CardHeader,
    Section,
    Widget,
    TextParagraph,
)


def test_text_paragraph_serialization() -> None:
    """Test that a basic text paragraph widget serializes correctly."""
    widget = Widget(textParagraph=TextParagraph(text="Hello, Chat!"))
    data = widget.to_dict()

    assert data == {"textParagraph": {"text": "Hello, Chat!"}}


def test_card_serialization_drops_none() -> None:
    """Test that the dictionary factory properly drops all None values."""
    header = CardHeader(title="Alert!", subtitle=None)  # subtitle is None
    data = header.to_dict()

    # "subtitle" should be completely missing from the dict
    assert data == {"title": "Alert!"}
    assert "subtitle" not in data


def test_full_card_assembly() -> None:
    """Test assembling a full V2 Card with sections and widgets."""
    card_message = CardWithId(
        cardId="unique-card-id",
        card=Card(
            header=CardHeader(
                title="System Status",
                subtitle="All systems operational",
                imageUrl="https://example.com/icon.png",
            ),
            sections=[
                Section(
                    header="Details",
                    widgets=[
                        Widget(textParagraph=TextParagraph(text="CPU usage is at 45%."))
                    ],
                )
            ],
        ),
    )

    data = card_message.to_dict()

    assert data == {
        "cardId": "unique-card-id",
        "card": {
            "header": {
                "title": "System Status",
                "subtitle": "All systems operational",
                "imageUrl": "https://example.com/icon.png",
            },
            "sections": [
                {
                    "header": "Details",
                    "widgets": [{"textParagraph": {"text": "CPU usage is at 45%."}}],
                }
            ],
        },
    }
