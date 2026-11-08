"""Authentication tests for the Homework 2 endpoints.

These run offline: no Langfuse, Docker, or model provider key. A rejected
request stops before the agent is built, so no model is ever called.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi import HTTPException

from server import app as server_app


@pytest.fixture
def clean_sessions(world: dict) -> Iterator[None]:
    """Use the temporary test database and start with no sessions."""
    server_app._SESSIONS.clear()
    yield
    server_app._SESSIONS.clear()


def test_create_session_rejects_role_mismatch(clean_sessions: None) -> None:
    """User 1 is a shopper, so claiming the support role must fail."""
    with pytest.raises(HTTPException) as rejected:
        server_app.create_session(
            server_app.SessionCreate(user_id=1, role="support")
        )

    assert rejected.value.status_code == 403
    assert server_app._SESSIONS == {}


def test_token_cannot_authorize_a_different_session(clean_sessions: None) -> None:
    """A valid token for one session must not unlock another session."""
    shopper = server_app.create_session(
        server_app.SessionCreate(user_id=1, role="shopper")
    )
    merchant = server_app.create_session(
        server_app.SessionCreate(user_id=9002, role="merchant")
    )

    with pytest.raises(HTTPException) as rejected:
        asyncio.run(
            server_app.post_message(
                merchant["session_id"],
                server_app.MessageIn(message="Show the store's orders."),
                authorization=f"Bearer {shopper['token']}",
            )
        )

    assert rejected.value.status_code == 403
