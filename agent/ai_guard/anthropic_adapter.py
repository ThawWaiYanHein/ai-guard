from .adapter_utils import patch_method
from .config import Config
from .observability import log_event

_PATCHED = False


def _import_class(module_name: str, class_name: str) -> type | None:
    try:
        return __import__(module_name, fromlist=[class_name]).__dict__.get(class_name)
    except Exception:
        return None


def _candidate_classes() -> list[tuple[type, str, str, bool]]:
    candidates: list[tuple[type, str, str, bool]] = []
    for module_name, class_names in (
        ("anthropic.resources.messages", ("Messages", "AsyncMessages")),
        ("anthropic.resources.messages.messages", ("Messages", "AsyncMessages")),
    ):
        for class_name in class_names:
            cls = _import_class(module_name, class_name)
            if cls is not None:
                candidates.append(
                    (
                        cls,
                        "create",
                        "anthropic.messages",
                        class_name.lower().startswith("async"),
                    )
                )
    return candidates


def patch_anthropic(config: Config | None = None) -> None:
    global _PATCHED
    if _PATCHED:
        return

    config = config or Config.from_env()
    patched = 0
    for cls, method_name, api, is_async in _candidate_classes():
        if patch_method(cls, method_name, api, config, is_async=is_async):
            patched += 1

    _PATCHED = True
    log_event(config, action="patched", reason=f"patched {patched} Anthropic resource classes")
