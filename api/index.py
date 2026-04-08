from pathlib import Path
import sys

# Ensure the project root is importable when executed in Vercel runtime.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app as flask_app  # noqa: E402

app = flask_app
