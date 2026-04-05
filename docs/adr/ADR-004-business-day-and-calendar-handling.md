# ADR-004: Business-Day And Calendar Handling

## Status

Accepted

## Date

2026-04-05

## Context

Multiple services will need prior-business-day and date-window behavior. If each service implements this independently, the repository will accumulate inconsistent comparison semantics.

## Decision

Business-day handling will be provided through shared or centrally governed calendar primitives rather than duplicated ad hoc inside individual services.

The initial foundation should support:

- prior business-day resolution
- deterministic handling of non-business gaps
- testable behavior under pinned fixture calendars

Holiday and market-calendar sophistication may expand later, but the first implementation must still use one shared abstraction path.

## Consequences

### Positive

- comparison-date semantics remain consistent
- deterministic services become easier to review
- replay behavior is easier to preserve

### Negative

- calendar concerns must be addressed earlier in the delivery plan
- some services cannot ship until the shared helper exists

## Alternatives considered

### Let each service implement its own date logic

Rejected because it creates hidden policy drift.

### Defer calendar handling entirely

Rejected because even the first risk-summary slice depends on prior-business-day semantics.
