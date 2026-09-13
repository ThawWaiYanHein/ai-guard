from functools import wraps
from typing import Any, Callable

from .cache import cache_key, can_cache, memory_cache
from .config import Config
from .firewall import inspect_payload
from .observability import increment, log_event

_PATCHED = False


def _patch_method(cls: type, method_name: str, api: str, config: Config, is_async: bool) -> None:
    current = getattr(cls, method_name, None)
    if current is None or getattr(current, "_ai_guard_patched", False):
        return

    if is_async:

        @wraps(current)
        async def async_wrapper(self, *args, **kwargs):
            guarded = _prepare(api, kwargs, config)
            cached = _cache_get(api, guarded, config)
            if cached is not None:
                return cached
            response = await current(self, *args, **guarded)
            _cache_set(api, guarded, response, config)
            return response

        async_wrapper._ai_guard_patched = True
        setattr(cls, method_name, async_wrapper)
        return

    @wraps(current)
    def wrapper(self, *args, **kwargs):
        guarded = _prepare(api, kwargs, config)
        cached = _cache_get(api, guarded, config)
        if cached is not None:
            return cached
        response = current(self, *args, **guarded)
        _cache_set(api, guarded, response, config)
        return response

    wrapper._ai_guard_patched = True
    setattr(cls, method_name, wrapper)


def _prepare(api: str, kwargs: dict[str, Any], config: Config) -> dict[str, Any]:
    result = inspect_payload(api, kwargs, config)
    return result.payload


def _cache_get(api: str, payload: dict[str, Any], config: Config) -> Any:
    if not config.cache_enabled or not can_cache(payload):
        return None
    key = cache_key(api, payload)
    cached = memory_cache.get(key)
    if cached is not None:
        increment("cache_hits")
        log_event(config, action="cache_hit", reason=f"{api} exact cache hit", model=payload.get("model"))
        return cached
    increment("cache_misses")
    return None


def _cache_set(api: str, payload: dict[str, Any], response: Any, config: Config) -> None:
    if config.cache_enabled and can_cache(payload):
        memory_cache.set(cache_key(api, payload), response, config.cache_ttl)


def _candidate_classes() -> list[tuple[type, str, bool]]:
    classes: list[tuple[type, str, bool]] = []

    def add(importer: Callable[[], tuple[type, type]], api: str) -> None:
        try:
            sync_cls, async_cls = importer()
            classes.append((sync_cls, api, False))
            classes.append((async_cls, api, True))
        except Exception:
            return

    add(
        lambda: __import__(
            "openai.resources.chat.completions.completions",
            fromlist=["Completions", "AsyncCompletions"],
        ).__dict__.get("Completions", None)
        and (
            __import__(
                "openai.resources.chat.completions.completions",
                fromlist=["Completions"],
            ).Completions,
            __import__(
                "openai.resources.chat.completions.completions",
                fromlist=["AsyncCompletions"],
            ).AsyncCompletions,
        ),
        "chat.completions",
    )
    add(
        lambda: (
            __import__("openai.resources.responses", fromlist=["Responses"]).Responses,
            __import__("openai.resources.responses", fromlist=["AsyncResponses"]).AsyncResponses,
        ),
        "responses",
    )
    add(
        lambda: (
            __import__(
                "openai.resources.responses.responses", fromlist=["Responses"]
            ).Responses,
            __import__(
                "openai.resources.responses.responses", fromlist=["AsyncResponses"]
            ).AsyncResponses,
        ),
        "responses",
    )
    return [(cls, api, is_async) for cls, api, is_async in classes if cls is not None]


def patch_openai(config: Config | None = None) -> None:
    global _PATCHED
    if _PATCHED:
        return

    config = config or Config.from_env()
    patched = 0
    for cls, api, is_async in _candidate_classes():
        _patch_method(cls, "create", api, config, is_async)
        patched += 1

    _PATCHED = True
    log_event(config, action="patched", reason=f"patched {patched} OpenAI resource classes")
