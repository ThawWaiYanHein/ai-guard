from .config import Config
from .observability import log_event
from .openai_adapter import patch_openai

_started = False


def init() -> None:
    global _started
    if _started:
        return

    config = Config.from_env()
    patch_openai(config)
    _started = True
    log_event(config, action="enabled", reason="openai instrumentation installed")
