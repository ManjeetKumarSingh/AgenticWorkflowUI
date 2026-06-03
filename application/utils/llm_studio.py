# utils/llm_studio.py

import json
import os
from typing import Any, Dict, Generator, List
from urllib import request, error
import json
import re


DEFAULT_LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
DEFAULT_LM_STUDIO_MODEL = "local-model"


class LmStudioError(RuntimeError):
    """Raised when strict LM Studio mode cannot complete a local model call."""


def get_llm_config(state: dict) -> Dict[str, Any]:
    """Resolve LM Studio settings from workflow state and environment."""
    config = state.get("llm_config") or {}
    return {
        "enabled": config.get("enabled", os.getenv("LM_STUDIO_ENABLED", "false").lower() == "true"),
        "base_url": config.get("base_url") or os.getenv("LM_STUDIO_URL", DEFAULT_LM_STUDIO_URL),
        "model": config.get("model") or os.getenv("LM_STUDIO_MODEL", DEFAULT_LM_STUDIO_MODEL),
        "timeout": int(config.get("timeout") or os.getenv("LM_STUDIO_TIMEOUT", "30")),
        "max_tokens": int(config.get("max_tokens") or os.getenv("LM_STUDIO_MAX_TOKENS", "450")),
        "require_llm": config.get("require_llm", False),
    }


def get_models_url(chat_completions_url: str) -> str:
    """Convert a chat completions URL to LM Studio's models URL."""
    if chat_completions_url.endswith("/chat/completions"):
        return chat_completions_url[: -len("/chat/completions")] + "/models"
    return chat_completions_url.rstrip("/") + "/models"


def list_lm_studio_models(chat_completions_url: str, timeout: int = 5) -> List[str]:
    """Fetch currently loaded/available models from LM Studio."""
    req = request.Request(get_models_url(chat_completions_url), method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
        response_json = json.loads(response_body)
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LmStudioError(f"Unable to connect to LM Studio models endpoint: {exc}") from exc

    models = []
    for item in response_json.get("data", []):
        model_id = item.get("id")
        if model_id:
            models.append(model_id)

    if not models:
        raise LmStudioError("LM Studio responded, but no local models were found")

    return models


def ask_lm_studio(
    state: dict,
    system_prompt: str,
    user_prompt: str,
    fallback: Dict[str, Any],
) -> Dict[str, Any]:
    """Call LM Studio's OpenAI-compatible chat endpoint and parse JSON output."""
    config = get_llm_config(state)
    if not config["enabled"]:
        return fallback

    payload = {
        "model": config["model"],
        "temperature": 0.2,
        "max_tokens": config["max_tokens"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        response_body = _post_chat_completion(payload, config)
        response_json = json.loads(response_body)
        content = response_json["choices"][0]["message"]["content"]
        parsed = json.loads(_extract_json(content))
        parsed["_llm_used"] = True
        return parsed
    except (error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError, LmStudioError) as exc:
        message = f"LM Studio call failed for model '{config['model']}': {exc}"
        if config["require_llm"]:
            raise LmStudioError(message) from exc

        fallback = fallback.copy()
        fallback["_llm_used"] = False
        fallback["_llm_error"] = message
        return fallback


def _post_chat_completion(payload: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Post to LM Studio, retrying without response_format for older servers."""
    try:
        return _post_json(config["base_url"], payload, config["timeout"])
    except error.HTTPError as exc:
        if exc.code != 400 or "response_format" not in payload:
            raise

        retry_payload = payload.copy()
        retry_payload.pop("response_format", None)
        return _post_json(config["base_url"], retry_payload, config["timeout"])


def _post_json(url: str, payload: Dict[str, Any], timeout: int) -> str:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


# def _extract_json(content: str) -> str:
#     """Handle models that wrap JSON in short explanatory text."""
#     content = content.strip()
#     if content.startswith("{") and content.endswith("}"):
#         return content

#     start = content.find("{")
#     end = content.rfind("}")
#     if start != -1 and end != -1 and end > start:
#         return content[start : end + 1]

#     raise ValueError("LM Studio response did not contain a JSON object")

def _extract_json(text):
    match = re.search(
        r'\{.*\}',
        text,
        re.DOTALL
    )
    if match:
        return json.loads(
            match.group()
        )
    return None


def chat_lm_studio_stream(
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout: int = 60,
    temperature: float = 0.7,
    max_tokens: int = -1,
) -> Generator[str, None, None]:
    """
    Stream a chat completion from LM Studio's OpenAI-compatible endpoint.
    Yields content tokens as they arrive via SSE.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
    }
    if max_tokens > 0:
        payload["max_tokens"] = max_tokens

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        base_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            buffer = ""
            while True:
                chunk = response.read(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            return
                        try:
                            chunk_json = json.loads(data)
                            delta = chunk_json["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass
    except (error.URLError, TimeoutError, ConnectionError) as exc:
        raise LmStudioError(f"Chat stream failed: {exc}") from exc
