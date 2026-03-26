"""
Dataclass models for constructing Google Chat V2 rich UI cards.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any, Dict


def _clean_dict_factory(data: List[tuple]) -> Dict[str, Any]:
    """Recursively removes keys with None values to satisfy the Google Chat API."""
    return {k: v for k, v in data if v is not None}


@dataclass
class BaseModel:
    """Base model providing dict serialization that drops None values."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self, dict_factory=_clean_dict_factory)


@dataclass
class TextParagraph(BaseModel):
    text: str


@dataclass
class Widget(BaseModel):
    textParagraph: Optional[TextParagraph] = None
    # Future widgets (Image, ButtonList, etc.) can be added here as Optional fields.


@dataclass
class Section(BaseModel):
    header: Optional[str] = None
    widgets: List[Widget] = field(default_factory=list)


@dataclass
class CardHeader(BaseModel):
    title: str
    subtitle: Optional[str] = None
    imageUrl: Optional[str] = None
    imageType: Optional[str] = None


@dataclass
class Card(BaseModel):
    header: Optional[CardHeader] = None
    sections: List[Section] = field(default_factory=list)


@dataclass
class CardWithId(BaseModel):
    cardId: str
    card: Card
