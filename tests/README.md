# Test Layout

Current visible test tree:
- `tests/unit/` for deterministic service and small wrapper tests
- `tests/replay/` for fixture-backed replay coverage of implemented services

Future slices may add integration and golden-case test directories when those
test types are introduced. They should be created in-slice rather than assumed
to already exist.

Repo-level `pytest` configuration already exists in `pyproject.toml`, so `pytest` is the default test entrypoint.

Bounded unit slices may still use stdlib `unittest` when that is the smallest coherent implementation path, but they should run cleanly under the repo's `pytest` baseline.
