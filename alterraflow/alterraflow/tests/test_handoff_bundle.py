"""Tests for the shared governed handoff bundle."""

from __future__ import annotations

import json
from pathlib import Path
import textwrap

from alterraflow.handoff_bundle import build_handoff_bundle
from alterraflow.orchestrator.state import PullRequestSnapshot


def _write_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(contents).lstrip(), encoding="utf-8")


def test_build_handoff_bundle_extracts_required_fields_and_resolves_links(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_file(repo_root / "docs" / "prds" / "phase-1" / "PRD-1.1-risk-summary-service-v2.md", "# PRD\n")
    _write_file(repo_root / "docs" / "adr" / "ADR-002-replay-and-snapshot-model.md", "# ADR-002\n")
    _write_file(repo_root / "docs" / "adr" / "ADR-003-trust-before-interpretation.md", "# ADR-003\n")
    work_item_path = repo_root / "work_items" / "ready" / "WI-MAINT-2A-shared-handoff-bundle-contract.md"
    _write_file(
        work_item_path,
        """
        # WI-MAINT-2A

        ## Linked PRD

        `docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`

        ## Linked ADRs

        - ADR-002
        - ADR-003

        ## Dependencies

        Blocking:

        - WI-MAINT-1A

        ## Scope

        - introduce one typed bundle
        - preserve multiline markdown bullets

        ## Target area

        - `alterraflow/handoff_bundle.py`
        - `alterraflow/tests/test_handoff_bundle.py`

        ## Out of scope

        - consumer migration

        ## Acceptance criteria

        - deterministic JSON serialization
        - deterministic markdown rendering

        ## Stop conditions

        - stop if this PR starts migrating runtime prompt builders
        """,
    )

    bundle = build_handoff_bundle(
        role="coding",
        work_item_path=work_item_path,
        repo_root=repo_root,
        runtime_metadata={
            "base_ref": "origin/main",
            "checkout_ref": "origin/codex/wi-maint-2a-shared-handoff-bundle",
            "checkout_detached": "true",
            "branch_owned_by_runtime": "false",
            "pr_head_branch": "codex/wi-maint-2a-shared-handoff-bundle",
            "worktree_path": "/tmp/runtime-worktree",
            "run_id": "run-123",
        },
        pull_request=PullRequestSnapshot(
            work_item_id="WI-MAINT-2A-shared-handoff-bundle-contract",
            number=201,
            is_draft=False,
            url="https://example.com/pr/201",
            head_ref_name="codex/wi-maint-2a-shared-handoff-bundle",
            base_ref_name="main",
            updated_at="2026-04-21T22:00:00Z",
            unresolved_review_threads=2,
            has_new_review_comments=True,
            review_decision="CHANGES_REQUESTED",
            merge_state_status="BLOCKED",
            ci_status="PENDING",
        ),
    )

    assert bundle.role == "coding"
    assert bundle.work_item_id == "WI-MAINT-2A-shared-handoff-bundle-contract"
    assert bundle.work_item_path == "work_items/ready/WI-MAINT-2A-shared-handoff-bundle-contract.md"
    assert bundle.checkout_context.checkout_detached is True
    assert bundle.checkout_context.branch_owned_by_runtime is False
    assert bundle.linked_prd is not None
    assert bundle.linked_prd.resolved_path == "docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md"
    assert [item.resolved_path for item in bundle.linked_adrs] == [
        "docs/adr/ADR-002-replay-and-snapshot-model.md",
        "docs/adr/ADR-003-trust-before-interpretation.md",
    ]
    assert "Blocking:" in bundle.dependencies
    assert bundle.scope == "- introduce one typed bundle\n- preserve multiline markdown bullets"
    assert bundle.target_area == "- `alterraflow/handoff_bundle.py`\n- `alterraflow/tests/test_handoff_bundle.py`"
    assert bundle.out_of_scope == "- consumer migration"
    assert bundle.acceptance_criteria == "- deterministic JSON serialization\n- deterministic markdown rendering"
    assert bundle.stop_conditions == "- stop if this PR starts migrating runtime prompt builders"
    assert bundle.pr_context is not None
    assert bundle.pr_context.number == 201
    assert bundle.source_provenance.runtime_metadata_keys == (
        "base_ref",
        "branch_owned_by_runtime",
        "checkout_detached",
        "checkout_ref",
        "pr_head_branch",
        "run_id",
        "worktree_path",
    )


def test_build_handoff_bundle_handles_missing_optional_fields(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    work_item_path = repo_root / "work_items" / "ready" / "WI-MAINT-EMPTY.md"
    _write_file(
        work_item_path,
        """
        # WI-MAINT-EMPTY

        ## Linked PRD

        None

        ## Linked ADRs

        None required.

        ## Dependencies

        None.

        ## Scope

        - one narrow contract slice

        ## Target area

        - `alterraflow/`

        ## Out of scope

        - runtime migration

        ## Acceptance criteria

        - builder exists
        """,
    )

    bundle = build_handoff_bundle(role="pm", work_item_path=work_item_path, repo_root=repo_root)

    assert bundle.linked_prd is None
    assert bundle.linked_adrs == ()
    assert bundle.stop_conditions is None
    assert bundle.pr_context is None
    assert bundle.checkout_context.base_ref is None
    assert bundle.source_provenance.pull_request_source is None


def test_handoff_bundle_serialization_and_markdown_are_deterministic(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_file(repo_root / "docs" / "prds" / "phase-1" / "PRD-1.1-risk-summary-service-v2.md", "# PRD\n")
    work_item_path = repo_root / "work_items" / "ready" / "WI-MAINT-STABLE.md"
    _write_file(
        work_item_path,
        """
        # WI-MAINT-STABLE

        ## Linked PRD

        PRD-1.1-v2

        ## Dependencies

        - WI-MAINT-1A

        ## Scope

        - first line
        - second line

        ## Target area

        - `alterraflow/`

        ## Out of scope

        - prompt migration

        ## Acceptance criteria

        - deterministic bytes

        ## Stop conditions

        - stop if consumer migration starts
        """,
    )

    first = build_handoff_bundle(
        role="review",
        work_item_path=work_item_path,
        repo_root=repo_root,
        runtime_metadata={"base_ref": "origin/main"},
    )
    second = build_handoff_bundle(
        role="review",
        work_item_path=work_item_path,
        repo_root=repo_root,
        runtime_metadata={"base_ref": "origin/main"},
    )

    assert first.to_json() == second.to_json()
    assert first.render_markdown() == second.render_markdown()

    payload = json.loads(first.to_json())
    assert payload["scope"] == "- first line\n- second line"
    assert payload["linked_prd"]["resolved_path"] == "docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md"
    assert "## Scope" in first.render_markdown()
    assert "- base_ref: `origin/main`" in first.render_markdown()


def test_render_markdown_handles_multiline_linked_prd_reference_with_backticks(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_file(repo_root / "docs" / "prds" / "phase-1" / "PRD-1.1-risk-summary-service-v2.md", "# PRD\n")
    work_item_path = repo_root / "work_items" / "ready" / "WI-MAINT-PRD-MULTILINE.md"
    _write_file(
        work_item_path,
        """
        # WI-MAINT-PRD-MULTILINE

        ## Linked PRD

        `docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`
        (supersedes `docs/prds/phase-0/PRD-0.9-risk-summary-service.md`)

        ## Dependencies

        None.

        ## Scope

        - preserve markdown formatting

        ## Target area

        - `alterraflow/`

        ## Out of scope

        - consumer migration

        ## Acceptance criteria

        - rendered markdown remains well formed
        """,
    )

    bundle = build_handoff_bundle(role="review", work_item_path=work_item_path, repo_root=repo_root)

    markdown = bundle.render_markdown()

    assert "## Linked PRD" in markdown
    assert "- reference_text:" in markdown
    assert "  `docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`" in markdown
    assert "  (supersedes `docs/prds/phase-0/PRD-0.9-risk-summary-service.md`)" in markdown
    assert "  - resolved_path: `docs/prds/phase-1/PRD-1.1-risk-summary-service-v2.md`" in markdown
    assert markdown.count("`") % 2 == 0


def test_build_handoff_bundle_resolves_prd_reference_with_explanatory_text(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_file(repo_root / "docs" / "prds" / "phase-2" / "PRD-2.1-shared-evidence-ref.md", "# PRD\n")
    work_item_path = repo_root / "work_items" / "done" / "WI-2.1.6-shared-evidence-ref-extraction.md"
    _write_file(
        work_item_path,
        """
        # WI-2.1.6

        ## Linked PRD

        PRD-2.1 (EvidenceRef schema and validation rules; gap closure in reuse analysis)

        ## Dependencies

        - WI-2.1.5

        ## Scope

        - keep linked PRD resolution stable

        ## Target area

        - `src/shared/`

        ## Out of scope

        - walker migration

        ## Acceptance criteria

        - linked PRD resolves
        """,
    )

    bundle = build_handoff_bundle(role="coding", work_item_path=work_item_path, repo_root=repo_root)

    assert bundle.linked_prd is not None
    assert bundle.linked_prd.resolved_path == "docs/prds/phase-2/PRD-2.1-shared-evidence-ref.md"
