from pathlib import Path

import pytest

from agent_runtime.handoff_bundle import build_handoff_bundle
from scripts.invoke import _fill_template


@pytest.fixture
def dummy_wi_path(tmp_path: Path) -> Path:
    wi_path = tmp_path / "work_items" / "ready" / "WI-TEST-1.1.md"
    wi_path.parent.mkdir(parents=True, exist_ok=True)
    wi_path.write_text(
        """# WI-TEST-1.1

## Purpose
Test manual handoff parity.

## Linked PRD
PRD-1.1

## Linked ADRs
- ADR-001
- ADR-002

## Dependencies
- WI-1.1.0

## Scope
- build things
- fix things

## Target Area
- src/test/

## Out Of Scope
- breaking things

## Acceptance Criteria
- things are built
- things are fixed

## Stop Conditions
- if it breaks
""",
        encoding="utf-8",
    )

    prd_path = tmp_path / "docs" / "prds" / "PRD-1.1-test.md"
    prd_path.parent.mkdir(parents=True, exist_ok=True)
    prd_path.write_text("# PRD 1.1")

    adr_path1 = tmp_path / "docs" / "adr" / "ADR-001-test.md"
    adr_path1.parent.mkdir(parents=True, exist_ok=True)
    adr_path1.write_text("# ADR 001")

    adr_path2 = tmp_path / "docs" / "adr" / "ADR-002-test.md"
    adr_path2.parent.mkdir(parents=True, exist_ok=True)
    adr_path2.write_text("# ADR 002")

    return wi_path


def test_template_filling_parity(dummy_wi_path: Path) -> None:
    repo_root = dummy_wi_path.parents[2]

    bundle = build_handoff_bundle(role="pm", work_item_path=dummy_wi_path, repo_root=repo_root)

    template = """
Here is the spec:
<LINKED_PRD>

And ADRs:
- <LINKED_ADRS>

Scope:
- <BULLETED_SCOPE_LIST — what the coding agent must build>

Target:
- <TARGET_FILES — exact file paths the agent should create or modify>

Out:
- <BULLETED_OUT_OF_SCOPE — explicit reminders of what not to touch>

Ac:
- <BULLETED_ACCEPTANCE_CRITERIA — what must be true when the slice is complete>

Stop:
- <BULLETED_STOP_CONDITIONS — when the agent should stop and report a blocker>
"""

    filled = _fill_template(template, bundle, extra={})

    assert "docs/prds/PRD-1.1-test.md" in filled
    assert "docs/adr/ADR-001-test.md" in filled
    assert "docs/adr/ADR-002-test.md" in filled
    assert "- build things" in filled
    assert "- src/test/" in filled
    assert "- breaking things" in filled
    assert "- things are built" in filled
    assert "- if it breaks" in filled
