# Test Layout

Use:
- `tests/unit/` for deterministic service and small wrapper tests
- `tests/integration/` for module and orchestrator integration tests
- `tests/replay/` for reproducibility and historical replay tests
- `tests/golden_cases/` for evaluation fixtures and expected outputs

Current unit slices may use stdlib `unittest` discovery when that is the smallest coherent path for a bounded PR.
`pytest` remains the preferred default once repo-level test configuration is introduced.
