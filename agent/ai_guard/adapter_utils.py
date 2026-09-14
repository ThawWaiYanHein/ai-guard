from functools import wraps
from typing import Any

from .cache import cache_key, can_cache, memory_cache
from .config import Config
from .firewall import inspect_payload
from .observability import increment, log_event


def patch_method(
    cls: type,
    method_name: str,
    api: str,
    config: Config,
    *,
    is_async: bool = False,
) -> bool:
    current = getattr(cls, method_name, None)
    if current is None or getattr(current, "_ai_guard_patched", False):
        return False

    if is_async:

        @wraps(current)
        async def async_wrapper(self, *args, **kwargs):
            guarded = prepare(api, kwargs, config)
            cached = cache_get(api, guarded, config)
            if cached is not None:
                return cached
            response = await current(self, *args, **guarded)
            cache_set(api, guarded, response, config)
            return response

        async_wrapper._ai_guard_patched = True
        setattr(cls, method_name, async_wrapper)
        return True

    @wraps(current)
    def wrapper(self, *args, **kwargs):
        guarded = prepare(api, kwargs, config)
        cached = cache_get(api, guarded, config)
        if cached is not None:
            return cached
        response = current(self, *args, **guarded)
        cache_set(api, guarded, response, config)
        return response

    wrapper._ai_guard_patched = True
    setattr(cls, method_name, wrapper)
    return True


def patch_function(module: Any, function_name: str, api: str, config: Config, *, is_async: bool = False) -> bool:
    current = getattr(module, function_name, None)
    if current is None or getattr(current, "_ai_guard_patched", False):
        return False

    if is_async:

        @wraps(current)
        async def async_wrapper(*args, **kwargs):
            guarded = prepare(api, kwargs, config)
            cached = cache_get(api, guarded, config)
            if cached is not None:
                return cached
            response = await current(*args, **guarded)
            cache_set(api, guarded, response, config)
            return response

        async_wrapper._ai_guard_patched = True
        setattr(module, function_name, async_wrapper)
        return True

    @wraps(current)
    def wrapper(*args, **kwargs):
        guarded = prepare(api, kwargs, config)
        cached = cache_get(api, guarded, config)
        if cached is not None:
            return cached
        response = current(*args, **guarded)
        cache_set(api, guarded, response, config)
        return response

    wrapper._ai_guard_patched = True
    setattr(module, function_name, wrapper)
    return True


def prepare(api: str, kwargs: dict[str, Any], config: Config) -> dict[str, Any]:
    result = inspect_payload(api, kwargs, config)
    return result.payload


def cache_get(api: str, payload: dict[str, Any], config: Config) -> Any:
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


def cache_set(api: str, payload: dict[str, Any], response: Any, config: Config) -> None:
    if config.cache_enabled and can_cache(payload):
        memory_cache.set(cache_key(api, payload), response, config.cache_ttl)
