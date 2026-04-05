# Mission and Design Principles

> **Note:** This document is the canonical design-principles reference. It combines the mission statement, system rationale, and detailed design principles in one place.

## Mission

Build an AI-supported market risk manager that helps detect, explain, challenge, escalate, and document material changes in risk.

The system is not a generic finance chatbot and not only a reporting layer. It is a governed operating capability that combines deterministic analytics, specialist AI walkers, workflow orchestration, and human decision gates to support real market risk management work.

The system must help answer questions such as:

- what changed in VaR, Expected Shortfall, desk status, or limits?
- why did it change?
- is the change a genuine market move, a concentration shift, a model effect, a data issue, a control issue, or a mixture?
- how confident are we in the explanation?
- what needs escalation, challenge, approval, documentation, or follow-up?

## Why this exists

In many institutions, market risk investigation is fragmented across reports, spreadsheets, control logs, ad hoc analysis, and individual judgment. This creates recurring problems:

- explanations are slow and inconsistent
- evidence is scattered
- simple questions require many manual joins
- weak data and control signals can be mistaken for market reality
- recurring governance tasks consume large amounts of expert time
- documentation quality varies across analysts and desks

The aim is not to remove accountable human judgment. The aim is to make high-quality risk management faster, more explicit, more replayable, and more challengeable.

## What the system is

The system is:

- a modular market risk operating platform
- an evidence-driven investigation environment
- a governed combination of deterministic services and specialist AI roles
- a human-supervised decision support capability

## What the system is not

The system is not:

- an autonomous sign-off authority
- a free-form chatbot that invents explanations without evidence
- a replacement for risk policy, governance, or accountable ownership
- a monolithic all-knowing agent with vague responsibilities

## Core design stance

The architecture intentionally separates:

- deterministic services that compute governed facts
- specialist walkers that investigate and interpret within bounded remits
- orchestrators that run business processes and route work
- human users who make accountable decisions at explicit decision gates

This separation exists to preserve clarity, testability, replayability, and challenge.

## Design principles

### 1. Evidence before narrative

Narrative is useful only when grounded in explicit evidence. The system must prefer:

- typed facts
- repeatable calculations
- traceable data lineage
- explicit caveats
- clear confidence states

over polished but weak prose.

### 2. Deterministic core first

Whenever a capability can be expressed as a deterministic service, it should be.

Deterministic services own:

- canonical calculations
- typed schemas
- business rules
- degraded states
- replay behavior
- fixture-driven tests

Walkers consume these services. They do not replace them.

### 3. AI where judgment synthesis is useful

Walkers exist where the system needs bounded interpretation across several evidence sources, for example:

- connecting change in risk to market context
- distinguishing plausible market explanations from suspicious ones
- identifying where a risk manager should challenge the initial story
- transforming technical findings into human-readable investigation outputs

### 4. Human accountability remains explicit

Humans remain responsible for:

- sign-off
- approval
- policy interpretation
- material challenge
- escalation decisions
- final governance judgment

The system supports these actions. It does not silently absorb them.

### 5. Challengeability is a first-class requirement

A good risk management system must make it easy to ask:

- what evidence supports this conclusion?
- what assumptions were used?
- what alternative explanations were considered?
- what is missing or uncertain?
- what would change the conclusion?

### 6. KISS and modularity

Modules must stay as simple as possible while still being useful.

The project follows:

- KISS
- YAGNI
- explicit interfaces
- small work items
- low-coupling module boundaries

### 7. Replayability and auditability

Important outputs must be reproducible from pinned data, pinned calendars, pinned snapshots, and pinned configuration.

The system must support:

- replay of deterministic services
- evidence capture for investigations
- stable reconstruction of prior cases
- explicit degraded and caveated states

### 8. Distinguish first-order from second-order risk

Simple delta is not the whole story.

The system must distinguish:

- first-order change: what moved between two dates
- second-order risk: how unstable, concentrated, or volatile the underlying series has become

### 9. Separate market reality from operational noise

One of the most important functions of a risk manager is distinguishing:

- genuine market moves
- data defects
- model changes
- control failures
- booking effects
- end-of-period mechanics

The architecture must preserve this distinction everywhere.

### 10. Outputs should support action

The best output is not merely interesting. It helps a risk manager decide:

- whether to investigate further
- whether to challenge the current explanation
- whether to escalate
- whether to document and close
- whether to raise a control or governance action

## Operating philosophy

The system should behave like a disciplined risk manager’s support team:

- deterministic services provide the books and instruments
- walkers conduct focused investigation within defined remits
- orchestrators run the operating rhythm
- humans decide, challenge, and sign off

## Success criteria

The project is successful if it materially improves:

- speed of investigation
- consistency of explanation
- clarity of evidence
- quality of challenge
- governance documentation quality
- replayability of prior conclusions
- separation of market signal from operational noise

## Implementation implications

This mission implies that future PRDs should always describe:

- what risk management question is being answered
- what human process the component supports
- what evidence it relies on
- what degraded states matter
- what decisions it influences
- what it must never do autonomously
