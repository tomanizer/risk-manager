---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 26px; }
  h1 { font-size: 1.6em; }
  h2 { font-size: 1.25em; }
  table { font-size: 0.85em; }
  code { font-size: 0.8em; }
footer: "Risk Manager — platform overview"
---

<!-- _class: lead -->
# Risk Manager
## AI-enabled market risk operating model

**Repository:** governed architecture for daily risk work *and* for how the repository itself is built.

---

## Objective (what the platform is for)

From the target operating model (`docs/00_tom_overview.md`):

- **Daily risk investigation** — explain moves with evidence, not narrative alone  
- **FRTB / PLA oversight** — structured controls lens (module roadmap)  
- **Limits and approvals** — policy and workflow (orchestrated, not ad-hoc chat)  
- **Controls & production integrity** — trust and lineage  
- **Desk status / capital consequence** — management-facing views  
- **Governance reporting** — repeatable packs  
- **Controlled change assessment** — change vs market attribution

**Non-goals:** autonomous sign-off, unconstrained “chatbot risk,” or a single monolithic agent owning everything.

---

## Design principle: three layers

```text
┌─────────────────────────────────────────────────────────┐
│  Process orchestrators   workflows, gates, handoffs     │
├─────────────────────────────────────────────────────────┤
│  Specialist walkers      bounded interpretation         │
├─────────────────────────────────────────────────────────┤
│  Capability modules      deterministic truth & rules    │
└─────────────────────────────────────────────────────────┘
```

- **Modules** own canonical calculations, typed state, degraded semantics, replay.  
- **Walkers** consume *typed* module outputs; they interpret, they do not replace truth.  
- **Orchestrators** own routing, challenge, and human decision points.

---

## Run the bank vs change the bank

| | **Run the bank** | **Change the bank** |
| --- | --- | --- |
| **Question** | What is risk? What moved? Is it unusual? | What do we ship next? Is the PR contract-faithful? |
| **Mechanism** | `src/modules/`, walkers, orchestrators | PRDs, `work_items/`, agent relay, `agent_runtime/` |
| **Authoritative outputs** | Typed summaries, history, statuses, replay | Merged code, tests, governed docs |
| **Where AI fits** | Specialist walkers (bounded interpretation) | PM / spec / coding / review / drift roles (governed relay) |

---

## What you will see in this deck

1. **Run the bank** — production capability: modules, deterministic APIs, walkers (risk interpretation).  
2. **Change the bank** — engineering governance: PRDs, work items, multi-agent relay, `agent_runtime`.  
3. **Worked example** — **Risk Analytics** and **PRD-1.1** (risk summary service): contracts, service surface, walker consumers.

*Terminology:* this repository standardizes on **PRD** (product/requirements documents) and governed **specs**; “BRD”-style business intent flows into PRDs and canon under `docs/`.

---

## Repository map (high level)

| Area | Role |
| --- | --- |
| `docs/` | Architecture canon, PRDs, methodology, engineering standards |
| `src/modules/` | Deterministic domain modules (e.g. `risk_analytics`, `controls_integrity`) |
| `prompts/agents/` | Standing instructions + invocation templates per agent role |
| `work_items/` | Bounded implementation slices with acceptance criteria |
| `agent_runtime/` | Optional automation: runners, orchestration graph, telemetry |
| `tests/`, `fixtures/` | Correctness and replay |
