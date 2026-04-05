# Runner Stubs

These files hold thin role-specific wrappers.

Each runner should:

- consume explicit typed inputs
- build the role-specific context bundle
- call the underlying model or agent runtime
- return structured output for the orchestrator

They should not own workflow routing logic.
