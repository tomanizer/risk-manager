# Skills (symlinks)

Each `*/SKILL.md` here is a **relative symlink** to `.cursor/skills/<name>/SKILL.md`.

**Edit the canonical file under `.cursor/skills/` only.** If you change a symlink target or add a skill, recreate the mirror entries the same way:

```bash
# From repository root (example: new-skill)
mkdir -p .github/skills/new-skill
ln -sf ../../../.cursor/skills/new-skill/SKILL.md .github/skills/new-skill/SKILL.md
ln -sf ../../.cursor/skills/new-skill/SKILL.md .claude/commands/new-skill.md
```

See also `.cursor/skills/README.md`.
