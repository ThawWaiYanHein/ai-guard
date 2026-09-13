import copy
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol


CACHE_FIELDS = {
    "model",
    "messages",
    "input",
    "instructions",
    "temperature",
    "max_tokens",
    "max_completion_tokens",
    "max_output_tokens",
    "tools",
    "tool_choice",
    "response_format",
    "text",
    "reasoning",
    "top_p",
    "seed",
    "stop",
}


class CacheBackend(Protocol):
    def get(self, key: str) -> Any: ...

    def set(self, key: str, value: Any, ttl: int) -> None: ...


@dataclass
class _Entry:
    value: Any
    expires_at: float


class MemoryCache:
    def __init__(self) -> None:
        self._items: dict[str, _Entry] = {}

    def get(self, key: str) -> Any:
        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            self._items.pop(key, None)
            return None
        return copy.deepcopy(entry.value)

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._items[key] = _Entry(copy.deepcopy(value), time.time() + ttl)


memory_cache = MemoryCache()


def can_cache(payload: dict[str, Any]) -> bool:
    if payload.get("stream"):
        return False
    if payload.get("tools") or payload.get("tool_choice"):
        return False
    if payload.get("previous_response_id") or payload.get("conversation"):
        return False
    return True


def cache_key(api: str, payload: dict[str, Any]) -> str:
    normalized = {
        key: payload.get(key)
        for key in sorted(CACHE_FIELDS)
        if key in payload and payload.get(key) is not None
    }
    data = {"api": api, "payload": normalized}
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
