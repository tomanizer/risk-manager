# Runner Stubs

These files hold thin role-specific wrappers.

Each runner should:

- consume explicit typed inputs
- build the role-specific context bundle
- call the underlying model or agent runtime
- return structured output for the orchestrator

They should not own workflow routing logic.

The PM runner now supports two modes:

- `prepared` (default): manual handoff only
- `codex_exec`: opt-in real backend using the local `codex exec` CLI

The review runner now supports the same two modes:

- `prepared` (default): manual handoff only
- `codex_exec`: opt-in real backend using the local `codex exec` CLI

The coding runner now supports the same two modes:

- `prepared` (default): manual handoff only
- `codex_exec`: opt-in real backend using the local `codex exec` CLI
