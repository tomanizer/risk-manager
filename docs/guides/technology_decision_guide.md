# Technology Decision Guide

## Purpose

This guide explains when and how technology decisions should be made for the AI-supported risk manager.

## Decision principle

Technology decisions should be made as late as possible, but not later.

That means:

- do not lock in tools before the capability shape is understood
- do not leave core technical choices ambiguous once they block implementation

## Decision layers

### Layer 1: mission and operating model

Decide first:

- what capability is being built
- whether it is deterministic or agentic
- what the human boundary is
- what evidence and replay requirements apply

### Layer 2: contract and data shape

Decide next:

- schemas
- status semantics
- scope semantics
- replay metadata
- persistence shape if relevant

### Layer 3: implementation technology

Only then decide:

- libraries
- framework choices
- storage engine
- orchestration framework
- UI framework

## How to make a technology decision

Use this template.

### 1. What problem are we solving?

State the real problem in one sentence.

### 2. What constraints matter?

For this project, common constraints include:

- Python 3.11+
- deterministic core first
- LangChain or LangGraph for agents where justified
- Pydantic for typed contracts
- SQLAlchemy 2+
- DuckDB
- Impala
- Dash for web apps
- replayability
- explicit degraded-state behavior

### 3. Is this a core architectural decision or a local implementation choice?

Examples of architectural decisions:

- whether agents are orchestrated in LangGraph
- whether canonical contracts use Pydantic
- whether DuckDB is used as a local analytical layer

Examples of local choices:

- exact file layout inside a module
- helper function names
- one testing utility versus another

### 4. What are the options?

Prefer two or three realistic options, not a zoo.

### 5. What criteria decide?

Typical criteria for this repo:

- simplicity
- fit with deterministic core design
- ease of testing
- replay friendliness
- local developer speed
- compatibility with the bank stack
- operational clarity

### 6. What do we choose now?

Record the decision briefly and explicitly.

### 7. What remains reversible?

A good decision note separates:

- what is fixed now
- what can still change later

## Recommended current stack stance

Given your stated stack, the recommended default is:

### Python 3.11+

Use as the project baseline for implementation.

### Pydantic

Use for typed contracts and request/response schemas.

Rationale:

- clear validation
- explicit serialization
- good fit for service contracts

### SQLAlchemy 2+

Use for relational access layers and integration boundaries where database-backed services are needed.

### DuckDB

Use as a local analytics engine, test harness aid, fixture exploration tool, and possibly lightweight computation substrate where appropriate.

### Impala

Treat as an enterprise data source boundary rather than as the center of local business logic.

### Dash

Use for analyst and governance-facing web applications when interactive views are needed.

### LangChain or LangGraph

Use only where agent orchestration is genuinely needed.

Recommended stance:

- deterministic modules do not need LangChain or LangGraph
- walkers and orchestrators are where LangGraph is more likely to be justified
- choose LangGraph when you need explicit multi-step graph orchestration and stateful agent flow
- choose simpler LangChain patterns only when the problem is lighter and does not need graph semantics

## How to decide between LangChain and LangGraph

Use LangGraph when:

- you need explicit nodes and edges
- you need state across multi-step agent flow
- you want strong control over routing and decision points
- you expect orchestrators and walker choreography to grow

Use simpler LangChain usage when:

- the task is prompt-plus-tooling without much graph structure
- the workflow is narrow and linear
- a graph would be ceremony rather than value

## Decision rhythm for this project

### Before implementation of a slice

PM agent should ask:

- does this slice require a tech decision now?
- or can we proceed with the existing default stack?

### During implementation

Coding agent should not make architectural tech choices silently.

If a choice is blocking, it should surface:

- the decision needed
- the options
- the impact

### Before merge

Review agent should check:

- did the PR introduce a hidden tech decision?
- was that decision explicit and justified?

## Practical guidance by phase

### Phase 1 deterministic core

Default to:

- Python 3.11+
- Pydantic
- pytest
- local fixtures
- simple package structure

Avoid bringing in agent frameworks too early.

### Agent and walker phase

Introduce LangGraph only when the deterministic core and contracts are sufficiently stable.

### Data integration phase

Use SQLAlchemy 2+ and Impala integrations once the contract layer and deterministic services are already solid.

### UI phase

Use Dash after service contracts and investigation flows are stable enough to avoid constant UI churn.

## Good decision examples

### Good

We will use Pydantic for PRD-1.1 contracts because explicit validation and serialization are needed immediately, and this choice is low-risk and aligned with later service APIs.

### Weak

We will probably use whatever agent framework feels easiest during implementation.

That is fog, not a decision.

## Recommendation for now

Your immediate technology baseline should be:

- Python 3.11+
- Pydantic for schemas
- pytest for tests
- SQLAlchemy 2+ where DB boundaries are needed
- DuckDB as local analytical support
- Impala as enterprise source boundary
- Dash later for analyst UI
- LangGraph later for walker and orchestrator composition, not for the deterministic foundation slice
