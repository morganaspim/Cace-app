from __future__ import annotations

import json

import pytest

from cace_studio.ai import local
from cace_studio.ai.provider import LocalAIError
from cace_studio.core.settings import StudioSettings


def test_ollama_model_discovery_and_chat(monkeypatch) -> None:
    calls = []

    def fake_request(url, *, method="GET", payload=None, timeout=5.0):
        calls.append((url, method, payload, timeout))
        if url.endswith("/api/tags"):
            return {"models": [{"name": "z-model"}, {"name": "a-model"}, {"name": "a-model"}]}
        if url.endswith("/api/chat"):
            return {"message": {"content": "answer"}}
        raise AssertionError(url)

    monkeypatch.setattr(local, "_request_json", fake_request)
    provider = local.create_local_provider("ollama", model="a-model", timeout=1.5)
    assert provider.list_models() == ("a-model", "z-model")
    assert provider.health().healthy is True
    assert provider.chat([{"role": "user", "content": "hello"}]) == "answer"
    chat_call = next(item for item in calls if item[0].endswith("/api/chat"))
    assert chat_call[1] == "POST"
    assert chat_call[2]["stream"] is False
    assert chat_call[2]["model"] == "a-model"


def test_openai_compatible_model_discovery_and_chat(monkeypatch) -> None:
    def fake_request(url, *, method="GET", payload=None, timeout=5.0):
        if url.endswith("/models"):
            return {"data": [{"id": "local-2"}, {"id": "local-1"}]}
        if url.endswith("/chat/completions"):
            assert method == "POST"
            assert payload["model"] == "local-1"
            return {"choices": [{"message": {"content": "local reply"}}]}
        raise AssertionError(url)

    monkeypatch.setattr(local, "_request_json", fake_request)
    provider = local.create_local_provider("lm-studio", model="local-1")
    assert provider.list_models() == ("local-1", "local-2")
    assert provider.chat([{"role": "user", "content": "question"}]) == "local reply"




def test_ollama_embeddings(monkeypatch) -> None:
    def fake_request(url, *, method="GET", payload=None, timeout=5.0):
        if url.endswith("/api/embed"):
            assert method == "POST"
            assert payload == {"model": "embed-model", "input": ["a", "b"]}
            return {"embeddings": [[1.0, 0.0], [0.0, 1.0]]}
        raise AssertionError(url)

    monkeypatch.setattr(local, "_request_json", fake_request)
    provider = local.create_local_provider("ollama", model="embed-model")
    assert provider.embeddings(["a", "b"]) == ((1.0, 0.0), (0.0, 1.0))


def test_openai_compatible_embeddings(monkeypatch) -> None:
    def fake_request(url, *, method="GET", payload=None, timeout=5.0):
        if url.endswith("/embeddings"):
            assert method == "POST"
            return {
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            }
        raise AssertionError(url)

    monkeypatch.setattr(local, "_request_json", fake_request)
    provider = local.create_local_provider("lm-studio", model="embed-model")
    assert provider.embeddings(["a", "b"]) == ((1.0, 0.0), (0.0, 1.0))


def test_local_provider_failures_are_explicit(monkeypatch) -> None:
    with pytest.raises(LocalAIError, match="unknown local AI provider"):
        local.create_local_provider("not-a-provider")

    provider = local.create_local_provider("ollama")
    with pytest.raises(LocalAIError, match="select an Ollama model"):
        provider.chat([{"role": "user", "content": "hello"}])

    def fail(*args, **kwargs):
        raise LocalAIError("offline")

    monkeypatch.setattr(local, "_request_json", fail)
    health = local.create_local_provider("ollama").health()
    assert health.healthy is False
    assert "offline" in health.detail


def test_detection_probes_loopback_defaults_only(monkeypatch) -> None:
    seen = []

    def fake_request(url, *, method="GET", payload=None, timeout=5.0):
        seen.append(url)
        if url.startswith("http://127.0.0.1:11434"):
            return {"models": [{"name": "m"}]}
        return {"data": []}

    monkeypatch.setattr(local, "_request_json", fake_request)
    results = local.detect_local_providers(timeout=0.01)
    assert [item.provider_id for item in results] == ["ollama", "lm-studio", "llama-cpp"]
    assert all(url.startswith("http://127.0.0.1:") for url in seen)


def test_studio_settings_persist_locally_with_ai_off_by_default(tmp_path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    monkeypatch.setenv("CACE_SETTINGS_PATH", str(path))
    settings = StudioSettings.load()
    assert settings.ai_enabled is False
    settings.ai_enabled = True
    settings.ai_provider = "lm-studio"
    settings.ai_endpoint = "http://127.0.0.1:1234/v1"
    settings.ai_model = "local-model"
    settings.assistant_mode = "teacher"
    assert settings.save() == path

    loaded = StudioSettings.load()
    assert loaded.ai_enabled is True
    assert loaded.ai_provider == "lm-studio"
    assert loaded.ai_model == "local-model"
    assert loaded.assistant_mode == "teacher"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["gpu_enabled"] is False


def test_studio_settings_ignore_unknown_fields_and_invalid_mode(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"assistant_mode":"impossible","future_field":123}', encoding="utf-8")
    settings = StudioSettings.load(path)
    assert settings.assistant_mode == "researcher"
    assert not hasattr(settings, "future_field")
