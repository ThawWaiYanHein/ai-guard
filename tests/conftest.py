import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "agent"

for path in (ROOT, AGENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
