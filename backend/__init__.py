"""Backend package initialization.

Ensures the local framework package can be imported as `designlab_core`
when the backend package is loaded from the repository root.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_framework_path = _project_root / "framework"

if str(_framework_path) not in sys.path:
    sys.path.insert(0, str(_framework_path))
