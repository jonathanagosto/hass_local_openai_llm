"""Tests for Local OpenAI LLM client creation."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from homeassistant.const import CONF_API_KEY
from openai._models import FinalRequestOptions, SecurityOptions

from custom_components.local_openai import _create_openai_client
from custom_components.local_openai.const import (
    AUTH_SCHEME_BEARER,
    AUTH_SCHEME_NO_PREFIX,
    CONF_AUTH_SCHEME,
    CONF_BASE_URL,
)


@pytest.fixture
def hass() -> MagicMock:
    """Mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_get_async_client(hass: MagicMock) -> Any:
    """Provide a real httpx client without a running Home Assistant."""
    with patch(
        "custom_components.local_openai.get_async_client",
        return_value=httpx.AsyncClient(),
    ):
        yield


def _data(**kwargs: Any) -> dict[str, Any]:
    return {
        CONF_BASE_URL: "http://localhost:8000/v1",
        CONF_API_KEY: "secret",
        CONF_AUTH_SCHEME: AUTH_SCHEME_BEARER,
        **kwargs,
    }


def test_create_client_bearer(hass: MagicMock) -> None:
    """Bearer scheme uses the built-in token header."""
    client = _create_openai_client(hass, _data())
    assert client.auth_headers.get("Authorization") == "Bearer secret"


def test_create_client_no_prefix(hass: MagicMock) -> None:
    """No-prefix scheme overrides the Authorization header with the raw key."""
    client = _create_openai_client(
        hass,
        _data(**{CONF_AUTH_SCHEME: AUTH_SCHEME_NO_PREFIX}),
    )
    assert client.default_headers.get("Authorization") == "secret"


def test_create_client_bearer_empty_key(hass: MagicMock) -> None:
    """Bearer scheme with an empty key creates an unauthenticated client."""
    client = _create_openai_client(hass, _data(**{CONF_API_KEY: ""}))
    assert client.default_headers.get("Authorization") == ""
    assert client.api_key == ""


def test_create_client_no_prefix_empty_key(hass: MagicMock) -> None:
    """No-prefix scheme with an empty key creates an unauthenticated client."""
    client = _create_openai_client(
        hass,
        _data(**{CONF_API_KEY: "", CONF_AUTH_SCHEME: AUTH_SCHEME_NO_PREFIX}),
    )
    assert client.default_headers.get("Authorization") == ""
    assert client.api_key == ""


def test_request_authorization_header_bearer(hass: MagicMock) -> None:
    """Bearer scheme sends the expected Authorization header on a request."""
    client = _create_openai_client(hass, _data())
    request = client._build_request(
        FinalRequestOptions(
            method="get",
            url="/models",
            security=SecurityOptions(bearer_auth=True),
        ),
    )
    assert request.headers["authorization"] == "Bearer secret"


def test_request_authorization_header_no_prefix(hass: MagicMock) -> None:
    """No-prefix scheme sends the raw key as the Authorization header."""
    client = _create_openai_client(
        hass,
        _data(**{CONF_AUTH_SCHEME: AUTH_SCHEME_NO_PREFIX}),
    )
    request = client._build_request(
        FinalRequestOptions(
            method="get",
            url="/models",
            security=SecurityOptions(bearer_auth=True),
        ),
    )
    assert request.headers["authorization"] == "secret"
