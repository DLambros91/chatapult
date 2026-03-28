"""Dataclass models for constructing Google Chat V2 rich UI cards."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any, Dict


def _clean_dict_factory(data: List[tuple]) -> Dict[str, Any]:
    """Recursively removes keys with None values to satisfy the Google Chat API."""
    return {k: v for k, v in data if v is not None}


@dataclass
class BaseModel:
    """Base Model."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model instance to a dictionary, removing keys with None values.

        Returns:
            A dictionary representation of the model, suitable for JSON serialization.
        """
        return asdict(self, dict_factory=_clean_dict_factory)


@dataclass
class TextParagraph(BaseModel):
    """TextParagraph widget.

    A simple widget that contains a block of text.
    """

    text: str


@dataclass
class Widget(BaseModel):
    """Widget.

    A single widget within a section of a card.
    """

    textParagraph: Optional[TextParagraph] = None
    # Future widgets (Image, ButtonList, etc.) can be added here as Optional fields.


@dataclass
class Section(BaseModel):
    """Section.

    A section of a card, which can include a header and multiple widgets.
    """

    header: Optional[str] = None
    widgets: List[Widget] = field(default_factory=list)


@dataclass
class CardHeader(BaseModel):
    """Card Header.

    The header of a card, which can include a title, subtitle, and an optional image.
    """

    title: str
    subtitle: Optional[str] = None
    imageUrl: Optional[str] = None
    imageType: Optional[str] = None


@dataclass
class Card(BaseModel):
    """Card.

    A standard Google Chat V2 Card, which can include an optional header and multiple
    sections.
    """

    header: Optional[CardHeader] = None
    sections: List[Section] = field(default_factory=list)


@dataclass
class CardWithId(BaseModel):
    """CardWithId.

    A wrapper for a Card that includes a unique cardId, as
    required by the API when sending cardsV2.
    """

    cardId: str
    card: Card

    @classmethod
    def create_simple(
        cls,
        card_id: str,
        title: str,
        text: str,
        subtitle: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> "CardWithId":
        """Helper method to instantly create a standard card without the boilerplate."""
        return cls(
            cardId=card_id,
            card=Card(
                header=CardHeader(title=title, subtitle=subtitle, imageUrl=image_url),
                sections=[
                    Section(widgets=[Widget(textParagraph=TextParagraph(text=text))])
                ],
            ),
        )
