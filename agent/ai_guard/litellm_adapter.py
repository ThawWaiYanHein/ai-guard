from .adapter_utils import patch_function
from .config import Config
from .observability import log_event

_PATCHED = False


def patch_litellm(config: Config | None = None) -> None:
    global _PATCHED
    if _PATCHED:
        return

    config = config or Config.from_env()
    patched = 0
    try:
        import litellm
    except Exception:
        litellm = None

    if litellm is not None:
        if patch_function(litellm, "completion", "litellm.completion", config):
            patched += 1
        if patch_function(litellm, "acompletion", "litellm.acompletion", config, is_async=True):
            patched += 1

    _PATCHED = True
    log_event(config, action="patched", reason=f"patched {patched} LiteLLM functions")
