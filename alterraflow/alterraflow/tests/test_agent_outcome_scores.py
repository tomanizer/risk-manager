"""Tests for the agent outcome score storage."""

from __future__ import annotations

import tempfile
from pathlib import Path

from alterraflow.storage.sqlite import (
    AgentOutcomeScore,
    load_agent_outcome_scores,
    record_agent_outcome_score,
)


def _tmp_db() -> Path:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        return Path(tmp.name)


def test_record_and_load_basic_score() -> None:
    db = _tmp_db()
    try:
        score = AgentOutcomeScore(
            run_id="test-run-001",
            work_item_id="WI-1.1.4-risk-summary-core-service",
            role="coding",
        )
        saved = record_agent_outcome_score(db, score)

        assert saved.score_id is not None
        assert saved.run_id == "test-run-001"
        assert saved.work_item_id == "WI-1.1.4-risk-summary-core-service"
        assert saved.role == "coding"
        assert saved.passed_stop_conditions is True
        assert saved.scope_respected is True
        assert saved.tests_green is True
        assert saved.review_rounds == 0
        assert saved.human_override is False
        assert saved.notes is None
        assert saved.scored_at is not None
    finally:
        db.unlink(missing_ok=True)


def test_record_score_with_all_fields() -> None:
    db = _tmp_db()
    try:
        score = AgentOutcomeScore(
            run_id="test-run-002",
            work_item_id="WI-1.1.4-risk-summary-core-service",
            role="coding",
            passed_stop_conditions=False,
            scope_respected=False,
            tests_green=True,
            review_rounds=3,
            human_override=True,
            notes="Agent went out of scope on error handling.",
        )
        saved = record_agent_outcome_score(db, score)

        assert saved.passed_stop_conditions is False
        assert saved.scope_respected is False
        assert saved.tests_green is True
        assert saved.review_rounds == 3
        assert saved.human_override is True
        assert saved.notes == "Agent went out of scope on error handling."
    finally:
        db.unlink(missing_ok=True)


def test_load_all_scores() -> None:
    db = _tmp_db()
    try:
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r1", work_item_id="WI-1.1.4", role="pm"))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r2", work_item_id="WI-1.1.4", role="coding"))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r3", work_item_id="WI-1.1.5", role="coding"))

        scores = load_agent_outcome_scores(db)
        assert len(scores) == 3
    finally:
        db.unlink(missing_ok=True)


def test_load_scores_filtered_by_work_item() -> None:
    db = _tmp_db()
    try:
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r1", work_item_id="WI-1.1.4", role="pm"))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r2", work_item_id="WI-1.1.4", role="coding"))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r3", work_item_id="WI-1.1.5", role="coding"))

        scores = load_agent_outcome_scores(db, work_item_id="WI-1.1.4")
        assert len(scores) == 2
        assert all(s.work_item_id == "WI-1.1.4" for s in scores)
    finally:
        db.unlink(missing_ok=True)


def test_load_scores_filtered_by_role() -> None:
    db = _tmp_db()
    try:
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r1", work_item_id="WI-1.1.4", role="pm"))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r2", work_item_id="WI-1.1.4", role="coding"))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r3", work_item_id="WI-1.1.5", role="coding"))

        scores = load_agent_outcome_scores(db, role="coding")
        assert len(scores) == 2
        assert all(s.role == "coding" for s in scores)
    finally:
        db.unlink(missing_ok=True)


def test_load_scores_filtered_by_both_role_and_work_item() -> None:
    db = _tmp_db()
    try:
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r1", work_item_id="WI-1.1.4", role="pm"))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r2", work_item_id="WI-1.1.4", role="coding"))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="r3", work_item_id="WI-1.1.5", role="coding"))

        scores = load_agent_outcome_scores(db, work_item_id="WI-1.1.4", role="pm")
        assert len(scores) == 1
        assert scores[0].run_id == "r1"
    finally:
        db.unlink(missing_ok=True)


def test_load_scores_returns_empty_list_when_none_recorded() -> None:
    db = _tmp_db()
    try:
        scores = load_agent_outcome_scores(db)
        assert scores == []
    finally:
        db.unlink(missing_ok=True)


def test_multiple_scores_per_run_are_allowed() -> None:
    db = _tmp_db()
    try:
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="same-run", work_item_id="WI-1.1.4", role="coding", review_rounds=1))
        record_agent_outcome_score(db, AgentOutcomeScore(run_id="same-run", work_item_id="WI-1.1.4", role="review", review_rounds=0))

        scores = load_agent_outcome_scores(db)
        assert len(scores) == 2
    finally:
        db.unlink(missing_ok=True)
