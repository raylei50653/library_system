import os
import json
from typing import Dict, List, Iterator, Optional
import httpx

DEFAULT_TIMEOUT_SEC = 30.0


def _parse_timeout_setting(raw_value: str) -> Optional[float]:
    """Return positive timeout seconds or None for unlimited/disabled."""
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return DEFAULT_TIMEOUT_SEC

    lowered = raw_value.lower()
    if lowered in {"none", "null", "infinite", "infinity"}:
        return None

    try:
        seconds = float(raw_value)
    except ValueError:
        return DEFAULT_TIMEOUT_SEC

    if seconds <= 0:
        return None

    return seconds


_timeout_setting = _parse_timeout_setting(os.getenv("OLLAMA_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC)))
if _timeout_setting is None:
    CLIENT_TIMEOUT = httpx.Timeout(timeout=None, connect=10.0)
    TIMEOUT_ERROR_MESSAGE = "Ollama did not respond before the request completed."
else:
    CLIENT_TIMEOUT = httpx.Timeout(timeout=_timeout_setting)
    TIMEOUT_ERROR_MESSAGE = (
        f"Ollama did not respond within {_timeout_setting:g} seconds. "
        "Increase OLLAMA_TIMEOUT_SEC if longer responses are expected."
    )

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
# 預設切到 qwen3:8b（可由 .env 覆寫）
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def chat_once(messages: List[Dict], model: str = DEFAULT_MODEL) -> str:
    """Call Ollama chat endpoint once (non-stream). Return assistant text.
    messages: [{"role": "system|user|assistant", "content": "..."}]
    """
    with httpx.Client(timeout=CLIENT_TIMEOUT) as client:
        last_error: Optional[str] = None
        for handler in (
            _chat_once_v1,
            _chat_once_api_chat,
            _chat_once_api_generate,
        ):
            try:
                content = handler(client, messages, model)
            except httpx.TimeoutException as exc:
                raise RuntimeError(TIMEOUT_ERROR_MESSAGE) from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    last_error = _extract_error_message(exc.response) or last_error
                    continue
                raise
            if content:
                return content
        if last_error:
            raise RuntimeError(last_error)
        return ""


def chat_stream(messages: List[Dict], model: str = DEFAULT_MODEL) -> Iterator[str]:
    """Yield text chunks from Ollama streaming chat API (line-delimited JSON)."""
    with httpx.Client(timeout=None) as client:
        last_error: Optional[str] = None
        for handler in (
            _chat_stream_v1,
            _chat_stream_api_chat,
            _chat_stream_api_generate,
        ):
            try:
                yield from handler(client, messages, model)
                return
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    last_error = _extract_error_message(exc.response) or last_error
                    continue
                raise
    # If we fall through without returning, no supported endpoint responded.
    message = last_error or "No supported Ollama chat endpoint responded successfully."
    raise RuntimeError(message)


def embed_texts(texts: List[str], model: str = EMBED_MODEL) -> List[List[float]]:
    """Get embeddings from Ollama embeddings API. Returns a list of vectors.
    用單一請求批量處理（Ollama 支援單條；這裡逐條呼叫以簡化）。
    """
    out: List[List[float]] = []
    with httpx.Client(timeout=CLIENT_TIMEOUT) as client:
        for t in texts:
            try:
                r = client.post(
                    f"{OLLAMA_URL}/v1/embeddings",
                    json={"model": model, "input": t},
                )
                r.raise_for_status()
                vec = _extract_embedding(r.json())
                if vec is not None:
                    out.append(vec)
                    continue
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise

            r = client.post(f"{OLLAMA_URL}/api/embeddings", json={"model": model, "prompt": t})
            r.raise_for_status()
            vec = _extract_embedding(r.json())
            out.append(vec or [])
    return out


def _prepare_generate_payload(
    messages: List[Dict],
    model: str,
    stream: bool,
) -> Dict:
    """Transform chat-style messages into a prompt for /api/generate."""
    system_chunks: List[str] = []
    conversation: List[str] = []

    for message in messages:
        role = (message.get("role") or "").lower()
        content = (message.get("content") or "").strip()
        if not content:
            continue

        if role == "system":
            system_chunks.append(content)
        elif role == "assistant":
            conversation.append(f"Assistant: {content}")
        else:
            # Treat anything not explicitly assistant/system as user.
            conversation.append(f"User: {content}")

    prompt_lines = conversation[:]
    if conversation and not conversation[-1].startswith("Assistant:"):
        prompt_lines.append("Assistant:")

    prompt = "\n".join(prompt_lines).strip()

    payload: Dict = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
    }

    if system_chunks:
        payload["system"] = "\n".join(system_chunks)

    return payload


def _chat_once_v1(client: httpx.Client, messages: List[Dict], model: str) -> str:
    r = client.post(
        f"{OLLAMA_URL}/v1/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
        },
    )
    r.raise_for_status()
    return _extract_content(r.json())


def _chat_once_api_chat(client: httpx.Client, messages: List[Dict], model: str) -> str:
    r = client.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
        },
    )
    r.raise_for_status()
    return _extract_content(r.json())


def _chat_once_api_generate(client: httpx.Client, messages: List[Dict], model: str) -> str:
    payload = _prepare_generate_payload(messages, model, stream=False)
    r = client.post(f"{OLLAMA_URL}/api/generate", json=payload)
    r.raise_for_status()
    return _extract_content(r.json())


def _chat_stream_v1(client: httpx.Client, messages: List[Dict], model: str) -> Iterator[str]:
    with client.stream(
        "POST",
        f"{OLLAMA_URL}/v1/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "stream": True,
        },
    ) as r:
        r.raise_for_status()
        yield from _iter_stream_chunks(r)


def _chat_stream_api_chat(client: httpx.Client, messages: List[Dict], model: str) -> Iterator[str]:
    with client.stream(
        "POST",
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": True,
        },
    ) as r:
        r.raise_for_status()
        yield from _iter_stream_chunks(r)


def _chat_stream_api_generate(client: httpx.Client, messages: List[Dict], model: str) -> Iterator[str]:
    payload = _prepare_generate_payload(messages, model, stream=True)
    with client.stream(
        "POST",
        f"{OLLAMA_URL}/api/generate",
        json=payload,
    ) as r:
        r.raise_for_status()
        yield from _iter_stream_chunks(r)


def _iter_stream_chunks(response: httpx.Response) -> Iterator[str]:
    for raw_line in response.iter_lines():
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line or line == "[DONE]":
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        chunk = _extract_content(obj)
        if chunk:
            yield chunk


def _extract_content(data: Dict) -> str:
    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if content:
            return content

    response_text = data.get("response")
    if isinstance(response_text, str) and response_text:
        return response_text

    choices = data.get("choices") or []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if content:
                return content
        delta = choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if content:
                return content
        text = choice.get("text")
        if isinstance(text, str) and text:
            return text

    return ""


def _extract_embedding(data: Optional[Dict]) -> Optional[List[float]]:
    if not isinstance(data, dict):
        return None

    embedding = data.get("embedding")
    if isinstance(embedding, list):
        return embedding

    items = data.get("data") or []
    for item in items:
        if not isinstance(item, dict):
            continue
        emb = item.get("embedding")
        if isinstance(emb, list):
            return emb

    return None


def _extract_error_message(response: httpx.Response) -> Optional[str]:
    try:
        data = response.json()
    except ValueError:
        data = None

    if isinstance(data, dict):
        msg = data.get("error") or data.get("detail")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    text = response.text.strip()
    if text:
        return text
    return None
