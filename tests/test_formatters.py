# SPDX-License-Identifier: Apache-2.0
"""Unit tests for chatapult.formatters helper functions."""

from chatapult.formatters import mention_all, mention_user


def test_mention_all() -> None:
    """mention_all() should return <users/all>."""
    assert mention_all() == "<users/all>"


def test_mention_user() -> None:
    """mention_user() should return <users/{user_id}>."""
    assert mention_user("12345") == "<users/12345>"


def test_mention_user_different_ids() -> None:
    """mention_user() should work with any user ID."""
    assert mention_user("abc") == "<users/abc>"
    assert mention_user("99999") == "<users/99999>"
