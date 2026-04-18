from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


CANONICAL_SKILLS_DIR = Path("skills")
CURSOR_SKILLS_DIR = Path(".cursor/skills")
CLAUDE_COMMANDS_DIR = Path(".claude/commands")
GITHUB_SKILLS_DIR = Path(".github/skills")
AGENTS_PATH = Path("AGENTS.md")
CANONICAL_README_PATH = CANONICAL_SKILLS_DIR / "README.md"
CURSOR_README_PATH = CURSOR_SKILLS_DIR / "README.md"
GITHUB_README_PATH = GITHUB_SKILLS_DIR / "README.md"
AGENTS_SKILLS_START = "<!-- BEGIN GENERATED SKILLS SECTION -->"
AGENTS_SKILLS_END = "<!-- END GENERATED SKILLS SECTION -->"
AGENTS_SKILLS_HEADER = "## Agent skills"
AGENTS_SKILLS_NEXT_HEADER = "## Freshness and branching rule"
GENERATED_MIRROR_MARKER = "<!-- GENERATED SKILL MIRROR: do not edit directly -->"


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    slug: str
    description: str
    canonical_path: Path
    content: str

    @property
    def claude_command(self) -> str:
        return f"/{self.slug}"

    @property
    def cursor_mirror_path(self) -> Path:
        return CURSOR_SKILLS_DIR / self.slug / "SKILL.md"

    @property
    def claude_mirror_path(self) -> Path:
        return CLAUDE_COMMANDS_DIR / f"{self.slug}.md"

    @property
    def github_mirror_path(self) -> Path:
        return GITHUB_SKILLS_DIR / self.slug / "SKILL.md"


def discover_skills(repo_root: Path) -> tuple[SkillDefinition, ...]:
    canonical_root = repo_root / CANONICAL_SKILLS_DIR
    if not canonical_root.is_dir():
        raise FileNotFoundError(f"Canonical skills directory `{CANONICAL_SKILLS_DIR.as_posix()}` is missing.")

    skill_paths = sorted(canonical_root.glob("*/SKILL.md"), key=lambda path: path.parent.name)
    skills = tuple(_parse_skill_definition(repo_root, path) for path in skill_paths)
    if not skills:
        raise ValueError(f"No canonical skills found under `{CANONICAL_SKILLS_DIR.as_posix()}`.")
    return skills


def expected_mirror_contents(repo_root: Path, skills: tuple[SkillDefinition, ...]) -> dict[Path, str]:
    expected: dict[Path, str] = {
        CANONICAL_README_PATH: render_canonical_readme(skills),
        CURSOR_README_PATH: render_cursor_readme(skills),
        GITHUB_README_PATH: render_github_readme(skills),
    }
    for skill in skills:
        mirror_content = render_mirror_content(skill.content)
        expected[skill.cursor_mirror_path] = mirror_content
        expected[skill.claude_mirror_path] = mirror_content
        expected[skill.github_mirror_path] = mirror_content
    existing_agents = (repo_root / AGENTS_PATH).read_text(encoding="utf-8")
    expected[AGENTS_PATH] = replace_agents_skills_section(existing_agents, skills)
    return expected


def stale_generated_paths(repo_root: Path, skills: tuple[SkillDefinition, ...]) -> tuple[Path, ...]:
    expected_cursor = {skill.cursor_mirror_path.as_posix() for skill in skills}
    expected_claude = {skill.claude_mirror_path.as_posix() for skill in skills}
    expected_github = {skill.github_mirror_path.as_posix() for skill in skills}

    stale: list[Path] = []
    for path in sorted((repo_root / CURSOR_SKILLS_DIR).glob("*/SKILL.md")):
        rel = path.relative_to(repo_root).as_posix()
        if rel not in expected_cursor and _is_generated_mirror_file(path):
            stale.append(path.relative_to(repo_root))
    for path in sorted((repo_root / CLAUDE_COMMANDS_DIR).glob("*.md")):
        rel = path.relative_to(repo_root).as_posix()
        if rel not in expected_claude and _is_generated_mirror_file(path):
            stale.append(path.relative_to(repo_root))
    for path in sorted((repo_root / GITHUB_SKILLS_DIR).glob("*/SKILL.md")):
        rel = path.relative_to(repo_root).as_posix()
        if rel not in expected_github and _is_generated_mirror_file(path):
            stale.append(path.relative_to(repo_root))
    return tuple(stale)


def apply_sync(repo_root: Path) -> tuple[SkillDefinition, ...]:
    skills = discover_skills(repo_root)
    expected = expected_mirror_contents(repo_root, skills)
    for relative_path, contents in expected.items():
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            destination.unlink()
        destination.write_text(contents, encoding="utf-8")

    for stale_path in stale_generated_paths(repo_root, skills):
        full_path = repo_root / stale_path
        full_path.unlink(missing_ok=True)
        _remove_empty_parent_directories(repo_root, full_path.parent)

    return skills


def find_mirror_drift(repo_root: Path) -> tuple[str, ...]:
    skills = discover_skills(repo_root)
    expected = expected_mirror_contents(repo_root, skills)
    findings: list[str] = []
    for relative_path, contents in expected.items():
        full_path = repo_root / relative_path
        if not full_path.is_file():
            findings.append(f"Missing generated file `{relative_path.as_posix()}`.")
            continue
        if full_path.is_symlink():
            findings.append(f"Generated file `{relative_path.as_posix()}` must be a real file, not a symlink.")
            continue
        actual = full_path.read_text(encoding="utf-8")
        if actual != contents:
            findings.append(f"Generated file `{relative_path.as_posix()}` is out of sync with canonical skills.")

    for stale_path in stale_generated_paths(repo_root, skills):
        findings.append(f"Unexpected generated skill mirror `{stale_path.as_posix()}` is present.")
    return tuple(findings)


def render_canonical_readme(skills: tuple[SkillDefinition, ...]) -> str:
    lines = [
        "# Skills",
        "",
        "This directory is the canonical source of truth for repository skills.",
        "",
        "Edit only `skills/<name>/SKILL.md`, then run `python scripts/skills/sync_skill_mirrors.py`.",
        "",
        "## Available skills",
        "",
        "| Skill | Claude command | Description |",
        "| --- | --- | --- |",
    ]
    for skill in skills:
        lines.append(f"| [{skill.slug}]({skill.slug}/SKILL.md) | `{skill.claude_command}` | {_escape_markdown_table_cell(skill.description)} |")
    lines.extend(
        [
            "",
            "## Generated mirrors",
            "",
            "| Location | Purpose |",
            "| --- | --- |",
            "| `.cursor/skills/<name>/SKILL.md` | Cursor-native skill discovery |",
            "| `.claude/commands/<name>.md` | Claude Code slash commands |",
            "| `.github/skills/<name>/SKILL.md` | GitHub / Copilot / VSCode discovery |",
            "",
            "## Maintenance",
            "",
            "After editing a canonical skill:",
            "",
            "```bash",
            "python scripts/skills/sync_skill_mirrors.py",
            "python scripts/skills/check_skill_mirrors.py",
            "```",
            "",
            "Generated mirrors are tracked in git so every supported platform can discover the same skill content without relying on symlinks.",
            "",
        ]
    )
    return "\n".join(lines)


def render_cursor_readme(skills: tuple[SkillDefinition, ...]) -> str:
    lines = [
        "# Cursor Skills",
        "",
        "This directory contains generated Cursor mirror files for the `risk-manager` repository.",
        "",
        "Do not edit files here by hand. Edit canonical skill content under `skills/` and re-run `python scripts/skills/sync_skill_mirrors.py`.",
        "",
        "## Available skills",
        "",
        "| Skill | Cursor invocation | Description |",
        "| --- | --- | --- |",
    ]
    for skill in skills:
        lines.append(f"| [{skill.slug}]({skill.slug}/SKILL.md) | `{skill.slug}` | {_escape_markdown_table_cell(skill.description)} |")
    lines.extend(
        [
            "",
            "## Canonical source",
            "",
            "- Canonical skill content: `skills/<name>/SKILL.md`",
            "- Claude Code mirrors: `.claude/commands/<name>.md`",
            "- GitHub / Copilot mirrors: `.github/skills/<name>/SKILL.md`",
            "",
            "The skills may also be copied to `~/.cursor/skills/<skill-name>/SKILL.md` for global Cursor workspaces, but the repository `skills/` tree remains canonical.",
            "",
        ]
    )
    return "\n".join(lines)


def render_github_readme(skills: tuple[SkillDefinition, ...]) -> str:
    lines = [
        "# Skills (generated mirrors)",
        "",
        "Each `*/SKILL.md` here is a generated mirror of the canonical file under `skills/<name>/SKILL.md`.",
        "",
        "Do not edit files here by hand.",
        "",
        "## Available skills",
        "",
        "| Skill | Mirror path | Description |",
        "| --- | --- | --- |",
    ]
    for skill in skills:
        lines.append(f"| `{skill.slug}` | `{skill.github_mirror_path.as_posix()}` | {_escape_markdown_table_cell(skill.description)} |")
    lines.extend(
        [
            "",
            "## Maintenance",
            "",
            "```bash",
            "python scripts/skills/sync_skill_mirrors.py",
            "python scripts/skills/check_skill_mirrors.py",
            "```",
            "",
            "See also `skills/README.md` and `.cursor/skills/README.md`.",
            "",
        ]
    )
    return "\n".join(lines)


def replace_agents_skills_section(contents: str, skills: tuple[SkillDefinition, ...]) -> str:
    pattern = re.compile(
        rf"^{re.escape(AGENTS_SKILLS_HEADER)}\n.*?(?=^{re.escape(AGENTS_SKILLS_NEXT_HEADER)}\n)",
        flags=re.MULTILINE | re.DOTALL,
    )
    replaced, count = pattern.subn(render_agents_skills_section(skills) + "\n", contents, count=1)
    if count != 1:
        raise ValueError("Could not locate the `## Agent skills` section in AGENTS.md.")
    return replaced


def render_agents_skills_section(skills: tuple[SkillDefinition, ...]) -> str:
    lines = [
        "## Agent skills",
        "",
        AGENTS_SKILLS_START,
        "",
        "Reusable agent skills are defined in `skills/` and generated into `.cursor/skills/`, `.claude/commands/`, and `.github/skills/` for platform-native discovery. Edit only `skills/<name>/SKILL.md`, then run `python scripts/skills/sync_skill_mirrors.py`. Most skills produce a filled invocation prompt for the correct specialist agent and **do not implement work themselves**. The **`babysit`** skill is the exception: it may run `git` / `gh`, triage threads, and push **small merge-readiness** commits per `skills/babysit/SKILL.md`.",
        "",
        "Available skills:",
        "",
        "| Skill | Invoke in Claude Code | Purpose |",
        "| --- | --- | --- |",
    ]
    for skill in skills:
        lines.append(f"| `{skill.slug}` | `{skill.claude_command}` | {_escape_markdown_table_cell(skill.description)} |")
    lines.extend(
        [
            "",
            "In Cursor, invoke by name in chat using the generated mirrors under `.cursor/skills/`. In Claude Code, use the `/skill-name` slash command from `.claude/commands/<skill>.md`. GitHub-oriented discovery can use `.github/skills/<skill>/SKILL.md`. In Codex, Copilot, VSCode, and other environments, point the agent at `skills/<skill>/SKILL.md` or reference the skill by name in your prompt.",
            "",
            AGENTS_SKILLS_END,
        ]
    )
    return "\n".join(lines)


def _parse_skill_definition(repo_root: Path, canonical_path: Path) -> SkillDefinition:
    if canonical_path.name != "SKILL.md":
        raise ValueError(f"Expected canonical skill file to be named `SKILL.md`, got `{canonical_path.name}`.")
    content = canonical_path.read_text(encoding="utf-8")
    metadata = _parse_frontmatter(content, canonical_path)
    slug = canonical_path.parent.name
    if metadata["name"] != slug:
        raise ValueError(
            f"Canonical skill `{canonical_path.relative_to(repo_root).as_posix()}` has frontmatter name `{metadata['name']}`; expected `{slug}`."
        )
    return SkillDefinition(
        slug=slug,
        description=metadata["description"],
        canonical_path=canonical_path.relative_to(repo_root),
        content=content,
    )


def _parse_frontmatter(content: str, path: Path) -> dict[str, str]:
    lines = content.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError(f"Skill file `{path.as_posix()}` is missing YAML frontmatter.")

    try:
        closing_index = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"Skill file `{path.as_posix()}` has an unterminated YAML frontmatter block.") from exc

    metadata_block = "\n".join(lines[1:closing_index])
    payload = yaml.safe_load(metadata_block)
    if not isinstance(payload, dict):
        raise ValueError(f"Skill file `{path.as_posix()}` frontmatter must decode to a mapping.")

    name = payload.get("name")
    description = payload.get("description")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Skill file `{path.as_posix()}` must define a non-empty string `name` in frontmatter.")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"Skill file `{path.as_posix()}` must define a non-empty string `description` in frontmatter.")
    return {"name": name.strip(), "description": description.strip()}


def render_mirror_content(content: str) -> str:
    lines = content.splitlines(keepends=True)
    if len(lines) >= 3 and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                remainder = "".join(lines[index + 1 :]).lstrip("\n")
                return "".join(lines[: index + 1]) + GENERATED_MIRROR_MARKER + "\n\n" + remainder
    return GENERATED_MIRROR_MARKER + "\n\n" + content.lstrip("\n")


def _is_generated_mirror_file(path: Path) -> bool:
    if not path.is_file():
        return False
    return GENERATED_MIRROR_MARKER in path.read_text(encoding="utf-8")


def _escape_markdown_table_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _remove_empty_parent_directories(repo_root: Path, start_dir: Path) -> None:
    current = start_dir
    protected = {
        repo_root / CURSOR_SKILLS_DIR,
        repo_root / CLAUDE_COMMANDS_DIR,
        repo_root / GITHUB_SKILLS_DIR,
    }
    while current not in protected and current != repo_root:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
