from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


class OllamaError(RuntimeError):
    pass


def generate(
    *,
    model: str,
    prompt: str,
    system: str | None = None,
    base_url: str = DEFAULT_OLLAMA_URL,
    temperature: float = 0.2,
    timeout: int = 300,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OllamaError(f"could not reach Ollama at {base_url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama returned invalid JSON") from exc

    text = data.get("response")
    if not isinstance(text, str):
        raise OllamaError("Ollama response did not include text")
    return text.strip()

