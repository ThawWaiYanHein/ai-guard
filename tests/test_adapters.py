import importlib
import sys

from ai_guard.config import Config


def _write_package(tmp_path, files):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def _clear_modules(*prefixes):
    for name in list(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(name, None)


def test_gemini_adapter_redacts_generate_content(tmp_path, monkeypatch):
    _write_package(
        tmp_path,
        {
            "google/__init__.py": "",
            "google/genai/__init__.py": "",
            "google/genai/models.py": """
class Models:
    def generate_content(self, **kwargs):
        return kwargs

class AsyncModels:
    async def generate_content(self, **kwargs):
        return kwargs
""",
        },
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    _clear_modules("google", "ai_guard.gemini_adapter")

    adapter = importlib.import_module("ai_guard.gemini_adapter")
    adapter._PATCHED = False
    adapter.patch_gemini(Config(cache_enabled=False))

    from google.genai.models import Models

    result = Models().generate_content(
        model="gemini-test",
        contents="email person@example.com and token sk-proj-abcdefghijklmnopqrstuvwxyz",
    )
    assert "[REDACTED_EMAIL]" in result["contents"]
    assert "[REDACTED_OPENAI_KEY]" in result["contents"]


def test_anthropic_adapter_redacts_messages(tmp_path, monkeypatch):
    _write_package(
        tmp_path,
        {
            "anthropic/__init__.py": "",
            "anthropic/resources/__init__.py": "",
            "anthropic/resources/messages.py": """
class Messages:
    def create(self, **kwargs):
        return kwargs

class AsyncMessages:
    async def create(self, **kwargs):
        return kwargs
""",
        },
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    _clear_modules("anthropic", "ai_guard.anthropic_adapter")

    adapter = importlib.import_module("ai_guard.anthropic_adapter")
    adapter._PATCHED = False
    adapter.patch_anthropic(Config(cache_enabled=False))

    from anthropic.resources.messages import Messages

    result = Messages().create(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": "email person@example.com and token sk-proj-abcdefghijklmnopqrstuvwxyz",
            }
        ],
    )
    content = result["messages"][0]["content"]
    assert "[REDACTED_EMAIL]" in content
    assert "[REDACTED_OPENAI_KEY]" in content


def test_litellm_adapter_redacts_completion(tmp_path, monkeypatch):
    _write_package(
        tmp_path,
        {
            "litellm.py": """
def completion(**kwargs):
    return kwargs

async def acompletion(**kwargs):
    return kwargs
""",
        },
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    _clear_modules("litellm", "ai_guard.litellm_adapter")

    adapter = importlib.import_module("ai_guard.litellm_adapter")
    adapter._PATCHED = False
    adapter.patch_litellm(Config(cache_enabled=False))

    import litellm

    result = litellm.completion(
        model="openai/fake",
        messages=[
            {
                "role": "user",
                "content": "email person@example.com and token sk-proj-abcdefghijklmnopqrstuvwxyz",
            }
        ],
    )
    content = result["messages"][0]["content"]
    assert "[REDACTED_EMAIL]" in content
    assert "[REDACTED_OPENAI_KEY]" in content
