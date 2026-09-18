from pathlib import Path

BASE = Path(__file__).parent


def build_system_prompt() -> str:
    parts = []

    system_file = BASE / "prompts" / "system_prompt.md"
    if system_file.exists():
        parts.append(system_file.read_text().strip())

    skills_dir = BASE / "skills"
    if skills_dir.exists():
        for skill_file in sorted(skills_dir.glob("*.md")):
            parts.append(f"\n---\n# Skill: {skill_file.stem}\n")
            parts.append(skill_file.read_text().strip())

    return "\n\n".join(parts)
