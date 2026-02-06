from __future__ import annotations

from pathlib import Path

import yaml


def export_skills_yaml(skills: list[dict], out_dir: str = "./exports/skills") -> list[Path]:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []

    for skill in skills:
        name = str(skill.get("name", "unnamed")).replace(" ", "_")
        out_path = root / f"{name}.yaml"
        out_path.write_text(yaml.safe_dump(skill, sort_keys=False), encoding="utf-8")
        out_paths.append(out_path)

    return out_paths
