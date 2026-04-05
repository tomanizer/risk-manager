# Storage Stub

The runtime needs durable state for:

- active work-item runs
- PR linkage
- last-seen review state
- blocked reasons
- retry and polling metadata

SQLite is the first local storage choice because it is simple, durable, and easy to inspect.
