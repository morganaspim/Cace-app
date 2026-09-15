from __future__ import annotations

import inspect

import pytest

from cace_studio.ai.local import (
    KNOWN_LOCAL_PROVIDERS,
    _NoRedirectHandler,
    create_local_provider,
)
from cace_studio.ai.provider import LocalAIError, validate_local_endpoint


@pytest.mark.parametrize(
    ("endpoint", "normalized"),
    [
        ("http://localhost:11434", "http://localhost:11434"),
        ("https://localhost", "https://localhost"),
        ("http://127.0.0.1:1234/v1/", "http://127.0.0.1:1234/v1"),
        ("http://127.8.9.10:9000/api", "http://127.8.9.10:9000/api"),
        ("http://[::1]:8080/v1", "http://[::1]:8080/v1"),
    ],
)
def test_validate_local_endpoint_accepts_only_loopback_forms(endpoint, normalized):
    assert validate_local_endpoint(endpoint) == normalized


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com:11434",
        "http://localhost.evil.example:11434",
        "http://192.168.1.10:11434",
        "http://8.8.8.8:11434",
        "ftp://127.0.0.1:11434",
        "http://user:pass@127.0.0.1:11434",
        "http://127.0.0.1:11434/path?target=http://example.com",
        "http://127.0.0.1:11434/#fragment",
        "http://127.0.0.1:99999",
        "http://127.0.0.1:11434/../admin",
        "http://127.0.0.1:11434/%2e%2e/admin",
        "http://127.0.0.1:11434/%252e%252e/admin",
        "http://127.0.0.1:11434/%2F%2Fevil.example",
        "http://127.0.0.1:11434/%255c%255cevil.example",
    ],
)
def test_validate_local_endpoint_rejects_remote_or_ambiguous_forms(endpoint):
    with pytest.raises(LocalAIError):
        validate_local_endpoint(endpoint)


def test_known_provider_defaults_and_factory_contract_are_preserved():
    expected_ids = {"ollama", "lm-studio", "llama-cpp", "openai-compatible"}
    assert set(KNOWN_LOCAL_PROVIDERS) == expected_ids

    signature = inspect.signature(create_local_provider)
    assert tuple(signature.parameters) == ("provider_id", "endpoint", "model", "timeout")
    assert signature.parameters["timeout"].kind is inspect.Parameter.KEYWORD_ONLY

    for provider_id, (_, default_endpoint) in KNOWN_LOCAL_PROVIDERS.items():
        provider = create_local_provider(provider_id, model="model-x", timeout=1.25)
        assert provider.endpoint == validate_local_endpoint(default_endpoint)
        assert provider.model == "model-x"
        assert provider.timeout == 1.25


def test_factory_rejects_remote_endpoint_before_network_io():
    with pytest.raises(LocalAIError):
        create_local_provider(
            "openai-compatible",
            "https://api.example.com/v1",
            "model-x",
        )


def test_redirect_handler_refuses_redirect_requests():
    handler = _NoRedirectHandler()
    assert (
        handler.redirect_request(
            None,
            None,
            302,
            "Found",
            {},
            "https://example.com/v1/models",
        )
        is None
    )
