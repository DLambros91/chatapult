# SPDX-License-Identifier: Apache-2.0
"""Helper functions for Google Chat mention formatting."""


def mention_all() -> str:
    """Return the mention string to notify all users in a space."""
    return "<users/all>"


def mention_user(user_id: str) -> str:
    """Return the mention string for a specific user by their ID."""
    return f"<users/{user_id}>"
