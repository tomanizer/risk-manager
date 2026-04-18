from __future__ import annotations

from pathlib import Path

from scripts.skills.common import (
    AGENTS_PATH,
    AGENTS_SKILLS_HEADER,
    AGENTS_SKILLS_NEXT_HEADER,
    CANONICAL_SKILLS_DIR,
    apply_sync,
    discover_skills,
    find_mirror_drift,
)


def test_discover_skills_parses_multiline_description(tmp_path: Path) -> None:
    _write_agents_stub(tmp_path)
    skill_path = tmp_path / CANONICAL_SKILLS_DIR / "demo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """---
name: demo
description: >-
  First sentence.
  Second sentence.
---

# demo
""",
        encoding="utf-8",
    )

    skills = discover_skills(tmp_path)

    assert len(skills) == 1
    assert skills[0].slug == "demo"
    assert skills[0].description == "First sentence. Second sentence."


def test_apply_sync_generates_all_mirror_surfaces(tmp_path: Path) -> None:
    _write_agents_stub(tmp_path)
    skill_path = tmp_path / CANONICAL_SKILLS_DIR / "demo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """---
name: demo
description: Demo description.
---

# demo
""",
        encoding="utf-8",
    )

    apply_sync(tmp_path)

    assert (tmp_path / "skills/README.md").is_file()
    assert (tmp_path / ".cursor/skills/demo/SKILL.md").read_text(encoding="utf-8") == skill_path.read_text(encoding="utf-8")
    assert (tmp_path / ".claude/commands/demo.md").read_text(encoding="utf-8") == skill_path.read_text(encoding="utf-8")
    assert (tmp_path / ".github/skills/demo/SKILL.md").read_text(encoding="utf-8") == skill_path.read_text(encoding="utf-8")

    agents_contents = (tmp_path / AGENTS_PATH).read_text(encoding="utf-8")
    assert "generated into `.cursor/skills/`, `.claude/commands/`, and `.github/skills/`" in agents_contents
    assert "`demo` | `/demo` | Demo description." in agents_contents


def test_find_mirror_drift_reports_missing_and_unexpected_files(tmp_path: Path) -> None:
    _write_agents_stub(tmp_path)
    skill_path = tmp_path / CANONICAL_SKILLS_DIR / "demo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """---
name: demo
description: Demo description.
---

# demo
""",
        encoding="utf-8",
    )
    (tmp_path / ".claude/commands/old-skill.md").parent.mkdir(parents=True)
    (tmp_path / ".claude/commands/old-skill.md").write_text("stale\n", encoding="utf-8")

    findings = find_mirror_drift(tmp_path)

    assert any("Missing generated file `.cursor/skills/demo/SKILL.md`." == finding for finding in findings)
    assert any("Unexpected generated skill mirror `.claude/commands/old-skill.md` is present." == finding for finding in findings)


def _write_agents_stub(root: Path) -> None:
    (root / AGENTS_PATH).write_text(
        "\n".join(
            [
                "# Repo",
                "",
                AGENTS_SKILLS_HEADER,
                "",
                "placeholder",
                "",
                AGENTS_SKILLS_NEXT_HEADER,
                "",
                "rest",
            ]
        ),
        encoding="utf-8",
    )
