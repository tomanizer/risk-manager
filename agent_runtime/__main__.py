"""CLI entry point for the repository agent runtime."""

from __future__ import annotations

from .orchestrator.graph import main


if __name__ == "__main__":
    raise SystemExit(main())
