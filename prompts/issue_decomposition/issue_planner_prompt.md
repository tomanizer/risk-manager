# Issue Decomposition Prompt

Given a PRD, decompose it into small, bounded issues.

Rules:
- keep issues narrow and testable
- separate schema work from service logic where possible
- separate workflow state from orchestration logic where possible
- include dependencies between issues
- identify parallelizable work
- do not redesign the PRD
- do not widen scope
