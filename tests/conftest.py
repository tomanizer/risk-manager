"""Shared pytest configuration."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

# Some CI collection environments do not place the repository root on sys.path,
# which breaks explicit imports like ``tests.unit...`` during test discovery.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
