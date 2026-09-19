from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .provider import AIProvider, LocalAIError, ProviderHealth, validate_local_endpoint


class _NoRedirectHandler(HTTPRedirectHandler):
    """Refuse redirects so a loopback service cannot bounce requests off-machine."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Ignore environment proxy variables. Optional local-AI traffic must stay local
# by construction rather than depending on machine proxy configuration.
_LOCAL_OPENER = build_opener(ProxyHandler({}), _NoRedirectHandler())


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: Mapping[str, Any] | None = None,
    timeout: float = 5.0,
) -> Any:
    safe_url = validate_local_endpoint(url)
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(safe_url, data=data, headers=headers, method=method)
    try:
        with _LOCAL_OPENER.open(request, timeout=timeout) as response:
            raw = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise LocalAIError(f"local AI request failed for {safe_url}: {exc}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalAIError(f"local AI returned invalid JSON from {safe_url}") from exc


class OllamaProvider(AIProvider):
    provider_id = "ollama"
    display_name = "Ollama"

    def list_models(self) -> tuple[str, ...]:
        data = _request_json(f"{self.endpoint}/api/tags", timeout=self.timeout)
        models = []
        for item in data.get("models", []) if isinstance(data, dict) else []:
            name = item.get("name") if isinstance(item, dict) else None
            if name:
                models.append(str(name))
        return tuple(sorted(set(models)))

    def health(self) -> ProviderHealth:
        try:
            models = self.list_models()
            return ProviderHealth(
                self.provider_id, self.display_name, self.endpoint, True, models, "reachable"
            )
        except LocalAIError as exc:
            return ProviderHealth(
                self.provider_id, self.display_name, self.endpoint, False, (), str(exc)
            )

    def chat(
        self, messages: Sequence[Mapping[str, str]], *, temperature: float = 0.2
    ) -> str:
        if not self.model:
            raise LocalAIError("select an Ollama model before sending a message")
        data = _request_json(
            f"{self.endpoint}/api/chat",
            method="POST",
            timeout=self.timeout,
            payload={
                "model": self.model,
                "messages": [
                    {"role": str(m["role"]), "content": str(m["content"])}
                    for m in messages
                ],
                "stream": False,
                "options": {"temperature": float(temperature)},
            },
        )
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LocalAIError("Ollama response did not contain message.content") from exc
        return str(content)

    def embeddings(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not self.model:
            raise LocalAIError("select an Ollama embedding model before requesting embeddings")
        requested = tuple(str(text) for text in texts)
        if not requested:
            return ()
        data = _request_json(
            f"{self.endpoint}/api/embed",
            method="POST",
            timeout=self.timeout,
            payload={"model": self.model, "input": list(requested)},
        )
        raw = data.get("embeddings") if isinstance(data, dict) else None
        if not isinstance(raw, list) or len(raw) != len(requested):
            raise LocalAIError("Ollama embedding response has the wrong shape")
        vectors = []
        width = None
        for vector in raw:
            if not isinstance(vector, list) or not vector:
                raise LocalAIError("Ollama embedding response contains an invalid vector")
            converted = tuple(float(value) for value in vector)
            if any(not math.isfinite(value) for value in converted):
                raise LocalAIError("Ollama embedding response contains non-finite values")
            width = len(converted) if width is None else width
            if len(converted) != width:
                raise LocalAIError("Ollama embedding response has inconsistent dimensions")
            vectors.append(converted)
        return tuple(vectors)


class OpenAICompatibleProvider(AIProvider):
    display_name = "OpenAI-compatible local server"

    def __init__(
        self,
        provider_id: str,
        endpoint: str,
        model: str = "",
        timeout: float = 30.0,
        display_name: str | None = None,
    ) -> None:
        super().__init__(endpoint, model, timeout)
        self.provider_id = provider_id
        if display_name:
            self.display_name = display_name

    def list_models(self) -> tuple[str, ...]:
        data = _request_json(f"{self.endpoint}/models", timeout=self.timeout)
        models = []
        for item in data.get("data", []) if isinstance(data, dict) else []:
            model_id = item.get("id") if isinstance(item, dict) else None
            if model_id:
                models.append(str(model_id))
        return tuple(sorted(set(models)))

    def health(self) -> ProviderHealth:
        try:
            models = self.list_models()
            return ProviderHealth(
                self.provider_id, self.display_name, self.endpoint, True, models, "reachable"
            )
        except LocalAIError as exc:
            return ProviderHealth(
                self.provider_id, self.display_name, self.endpoint, False, (), str(exc)
            )

    def chat(
        self, messages: Sequence[Mapping[str, str]], *, temperature: float = 0.2
    ) -> str:
        if not self.model:
            raise LocalAIError("select a local model before sending a message")
        data = _request_json(
            f"{self.endpoint}/chat/completions",
            method="POST",
            timeout=self.timeout,
            payload={
                "model": self.model,
                "messages": [
                    {"role": str(m["role"]), "content": str(m["content"])}
                    for m in messages
                ],
                "temperature": float(temperature),
                "stream": False,
            },
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LocalAIError(
                "OpenAI-compatible response did not contain choices[0].message.content"
            ) from exc
        return str(content)

    def embeddings(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not self.model:
            raise LocalAIError("select a local embedding model before requesting embeddings")
        requested = tuple(str(text) for text in texts)
        if not requested:
            return ()
        data = _request_json(
            f"{self.endpoint}/embeddings",
            method="POST",
            timeout=self.timeout,
            payload={"model": self.model, "input": list(requested)},
        )
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list) or len(rows) != len(requested):
            raise LocalAIError("OpenAI-compatible embedding response has the wrong shape")
        if all(isinstance(row, dict) and isinstance(row.get("index"), int) for row in rows):
            rows = sorted(rows, key=lambda row: row["index"])
        vectors = []
        width = None
        for row in rows:
            vector = row.get("embedding") if isinstance(row, dict) else None
            if not isinstance(vector, list) or not vector:
                raise LocalAIError("OpenAI-compatible embedding response contains an invalid vector")
            converted = tuple(float(value) for value in vector)
            if any(not math.isfinite(value) for value in converted):
                raise LocalAIError("OpenAI-compatible embedding response contains non-finite values")
            width = len(converted) if width is None else width
            if len(converted) != width:
                raise LocalAIError("OpenAI-compatible embedding response has inconsistent dimensions")
            vectors.append(converted)
        return tuple(vectors)


KNOWN_LOCAL_PROVIDERS = {
    "ollama": ("Ollama", "http://127.0.0.1:11434"),
    "lm-studio": ("LM Studio", "http://127.0.0.1:1234/v1"),
    "llama-cpp": ("llama.cpp", "http://127.0.0.1:8080/v1"),
    "openai-compatible": (
        "OpenAI-compatible local server",
        "http://127.0.0.1:1234/v1",
    ),
}


def create_local_provider(
    provider_id: str,
    endpoint: str = "",
    model: str = "",
    *,
    timeout: float = 30.0,
) -> AIProvider:
    provider_id = provider_id.strip().lower()
    if provider_id not in KNOWN_LOCAL_PROVIDERS:
        raise LocalAIError(f"unknown local AI provider: {provider_id}")
    display_name, default_endpoint = KNOWN_LOCAL_PROVIDERS[provider_id]
    endpoint = endpoint or default_endpoint
    if provider_id == "ollama":
        return OllamaProvider(endpoint, model, timeout)
    return OpenAICompatibleProvider(
        provider_id, endpoint, model, timeout, display_name
    )


def detect_local_providers(*, timeout: float = 0.6) -> tuple[ProviderHealth, ...]:
    """Probe well-known loopback endpoints only.

    Detection never contacts the public internet and does not change settings.
    """
    results = []
    for provider_id in ("ollama", "lm-studio", "llama-cpp"):
        provider = create_local_provider(provider_id, timeout=timeout)
        results.append(provider.health())
    return tuple(results)
