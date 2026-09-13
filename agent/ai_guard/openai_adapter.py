from typing import Callable

from .adapter_utils import patch_method
from .config import Config
from .observability import log_event

_PATCHED = False


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
        if patch_method(cls, "create", api, config, is_async=is_async):
            patched += 1

    _PATCHED = True
    log_event(config, action="patched", reason=f"patched {patched} OpenAI resource classes")
