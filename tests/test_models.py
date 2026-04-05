"""Tests for the V2 Card dataclass models."""

from chatapult.models import (
    CardWithId,
    Card,
    CardHeader,
    Section,
    Widget,
    TextParagraph,
    OpenLink,
    OnClick,
    Button,
    ButtonList,
)


def test_text_paragraph_serialization() -> None:
    """Test that a basic text paragraph widget serializes correctly."""
    widget = Widget(textParagraph=TextParagraph(text="Hello, Chat!"))
    data = widget.to_dict()

    assert data == {"textParagraph": {"text": "Hello, Chat!"}}


def test_button_list_serialization() -> None:
    """Test that a button list with button and open link serializes correctly."""
    open_link = OpenLink(url="https://github.com/DLambros91/chatapult")
    on_click = OnClick(openLink=open_link)
    button = Button(text="Chatapult Github", onClick=on_click)

    widget = Widget(buttonList=ButtonList(buttons=[button]))

    data = widget.to_dict()

    assert data == {
        "buttonList": {
            "buttons": [
                {
                    "text": "Chatapult Github",
                    "onClick": {
                        "openLink": {"url": "https://github.com/DLambros91/chatapult"}
                    },
                }
            ]
        }
    }


def test_multiple_buttons_serialization() -> None:
    """Test that multiple buttons in a buttonList are serialized."""
    button1 = Button(
        text="Button 1", onClick=OnClick(openLink=OpenLink(url="url_test1"))
    )
    button2 = Button(
        text="Button 2", onClick=OnClick(openLink=OpenLink(url="url_test2"))
    )

    widget = Widget(buttonList=ButtonList(buttons=[button1, button2]))
    data = widget.to_dict()

    assert len(data["buttonList"]["buttons"]) == 2
    assert data["buttonList"]["buttons"][1]["text"] == "Button 2"


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


def test_create_simple_card() -> None:
    """Test the create_simple class method for quickly making a basic card.

    This should create a card with the provided title and text, and leave
    optional fields as None.
    """
    card = CardWithId.create_simple(card_id="test", title="Alert", text="CPU 99%")
    assert card.cardId == "test"
    assert card.card.header is not None
    assert card.card.header.title == "Alert"
    assert card.card.sections[0].widgets[0].textParagraph is not None
    assert card.card.sections[0].widgets[0].textParagraph.text == "CPU 99%"
