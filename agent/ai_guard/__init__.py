from .config import Config
from .anthropic_adapter import patch_anthropic
from .gemini_adapter import patch_gemini
from .litellm_adapter import patch_litellm
from .observability import log_event
from .openai_adapter import patch_openai

_started = False


def init() -> None:
    global _started
    if _started:
        return

    config = Config.from_env()
    patch_openai(config)
    patch_gemini(config)
    patch_anthropic(config)
    patch_litellm(config)
    _started = True
    log_event(config, action="enabled", reason="provider instrumentation installed")
