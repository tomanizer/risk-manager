from __future__ import annotations

from pathlib import Path

from scripts.skills.common import (
    AGENTS_PATH,
    AGENTS_SKILLS_HEADER,
    AGENTS_SKILLS_NEXT_HEADER,
    CANONICAL_SKILLS_DIR,
    GENERATED_MIRROR_MARKER,
    apply_sync,
    discover_skills,
    find_mirror_drift,
    render_mirror_content,
)
import scripts.skills.common as skills_common


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
    expected_mirror = render_mirror_content(skill_path.read_text(encoding="utf-8"))
    assert (tmp_path / ".cursor/skills/demo/SKILL.md").read_text(encoding="utf-8") == expected_mirror
    assert (tmp_path / ".claude/commands/demo.md").read_text(encoding="utf-8") == expected_mirror
    assert (tmp_path / ".github/skills/demo/SKILL.md").read_text(encoding="utf-8") == expected_mirror

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
    stale_generated = tmp_path / ".claude/commands/old-skill.md"
    stale_generated.parent.mkdir(parents=True)
    stale_generated.write_text(f"{GENERATED_MIRROR_MARKER}\nstale\n", encoding="utf-8")
    unrelated_command = tmp_path / ".claude/commands/custom-user-command.md"
    unrelated_command.write_text("user-defined\n", encoding="utf-8")

    findings = find_mirror_drift(tmp_path)

    assert any("Missing generated file `.cursor/skills/demo/SKILL.md`." == finding for finding in findings)
    assert any("Unexpected generated skill mirror `.claude/commands/old-skill.md` is present." == finding for finding in findings)
    assert all("custom-user-command.md" not in finding for finding in findings)


def test_discover_skills_rejects_non_string_frontmatter_fields(tmp_path: Path) -> None:
    _write_agents_stub(tmp_path)
    skill_path = tmp_path / CANONICAL_SKILLS_DIR / "demo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """---
name: demo
description: 123
---

# demo
""",
        encoding="utf-8",
    )

    try:
        discover_skills(tmp_path)
    except ValueError as exc:
        assert "non-empty string `description`" in str(exc)
    else:
        raise AssertionError("Expected malformed frontmatter to raise ValueError.")


def test_discover_skills_parses_frontmatter_without_pyyaml(tmp_path: Path, monkeypatch) -> None:
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

    monkeypatch.setattr(skills_common, "_yaml", None)

    skills = discover_skills(tmp_path)

    assert len(skills) == 1
    assert skills[0].description == "First sentence. Second sentence."


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
