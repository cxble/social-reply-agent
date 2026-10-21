"""Compatibility shim for tools run as `python3 tools/<script>.py`."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.normalize import CORE, NORMALIZE, bare_interjection, is_empty, normalize

__all__ = ["CORE", "NORMALIZE", "bare_interjection", "is_empty", "normalize"]
