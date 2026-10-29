"""Loads skill prompts straight from .agents/skills/ — single source of truth,
no duplicated prompt text in Python (mounted read-only into the container)."""
from functools import lru_cache
from pathlib import Path

SKILLS_DIR = Path(".agents/skills")
if not SKILLS_DIR.exists():
    _repo_root_skills = Path(__file__).resolve().parents[3] / ".agents" / "skills"
    if _repo_root_skills.exists():
        SKILLS_DIR = _repo_root_skills

OUTPUT_SUFFIX = "\n\nBalas HANYA dengan satu objek JSON sesuai format contoh di atas. Jangan sertakan teks lain, markdown, atau penjelasan di luar JSON."


@lru_cache
def load_skill_prompt(skill_name: str) -> str:
    path = SKILLS_DIR / skill_name / "SKILL.md"
    return path.read_text(encoding="utf-8") + OUTPUT_SUFFIX
