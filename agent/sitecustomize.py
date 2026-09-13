import os
import sys


if os.getenv("AI_GUARD_ENABLED", "").lower() == "true":
    try:
        import ai_guard

        ai_guard.init()
    except Exception as exc:
        print(f"[AI-GUARD] initialization failed: {exc}", file=sys.stderr)
