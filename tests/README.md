# Test Layout

Current visible test tree:
- `tests/unit/` for deterministic service and small wrapper tests

Reserved future directories, when those slices land:
- `tests/integration/` for module and orchestrator integration tests
- `tests/replay/` for reproducibility and historical replay tests
- `tests/golden_cases/` for evaluation fixtures and expected outputs

Repo-level `pytest` configuration already exists in `pyproject.toml`, so `pytest` is the default test entrypoint.

Bounded unit slices may still use stdlib `unittest` when that is the smallest coherent implementation path, but they should run cleanly under the repo's `pytest` baseline.
