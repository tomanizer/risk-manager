# Storage Stub

The runtime needs durable state for:

- active work-item runs
- PR linkage
- last-seen review state
- blocked reasons
- retry and polling metadata

SQLite is the first local storage choice because it is simple, durable, and easy to inspect.

The current state store records:

- the last relay action per work item
- linked PR number and branch when known
- blocked reason for spec-routing cases
- runner metadata needed to resume or audit the next handoff
- the latest local runner result summary and payload
- the reviewed manual outcome recorded after a real PM/spec/coding/review session
- active and released linked worktree leases per runner run
