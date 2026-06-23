"""Return available prompt category filters from bundled templates."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

import yaml

from config import bundled_data_dir, user_data_dir
from library_update import load_update_meta

MAX_PROMPTS = 50
FILTER_ALL = "All Categories"
TeamMode = Literal["red", "purple"]

PURPLE_TEAM_NOTE = (
    "Purple team: record model response, map finding to OWASP LLM / MITRE ATLAS, "
    "and share artifacts with blue team for control validation."
)


@dataclass
class PromptIdea:
    index: int
    name: str
    source: str
    repository: str
    technique: str
    category: str
    text: str


def _load_yaml_template(path: Path) -> Optional[dict]:
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except Exception:
        return None


def _render_template_value(value: str, context: str) -> str:
    text = value or ""
    text = text.replace("{{ prompt }}", context)
    text = text.replace("{{prompt}}", context)
    text = re.sub(r"\{\{\s*prompt\s*\}\}", context, text)
    return text.strip()


def _discover_templates() -> List[tuple[Path, dict]]:
    by_stem: dict[str, tuple[Path, dict]] = {}
    for root in (bundled_data_dir(), user_data_dir()):
        template_dir = root / "templates"
        if not template_dir.is_dir():
            continue
        for path in sorted(template_dir.glob("*.yaml")):
            data = _load_yaml_template(path)
            if data and data.get("value"):
                by_stem[path.stem] = (path, data)
    return list(by_stem.values())


def _repo_label(data: dict, path: Path) -> str:
    source = str(data.get("source") or "")
    name = path.stem.lower()
    if "garak" in source.lower() or "garak" in name:
        return "Garak (NVIDIA)"
    if "owasp" in source.lower() or "owasp" in name:
        return "OWASP LLM Top 10"
    if "promptfoo" in source.lower() or "promptfoo" in name:
        return "Promptfoo"
    if "nist" in source.lower() or "nist" in name:
        return "NIST AI RMF"
    if "atlas" in source.lower() or "atlas" in name:
        return "MITRE ATLAS"
    if source.startswith("http"):
        return source
    return "Bundled Technique Library"


def list_category_filters() -> List[str]:
    categories = sorted({str(d.get("category") or "General") for _, d in _discover_templates()})
    return [FILTER_ALL, *categories]


def load_repositories() -> list:
    for root in (user_data_dir(), bundled_data_dir()):
        repo_file = root / "repositories.json"
        if repo_file.is_file():
            with repo_file.open(encoding="utf-8") as fh:
                return json.load(fh)
    return []


def generate_prompt_ideas(
    context: str,
    limit: int = MAX_PROMPTS,
    team_mode: TeamMode = "red",
    category_filter: str = FILTER_ALL,
) -> List[PromptIdea]:
    context = (context or "").strip()
    if not context:
        return []

    templates = _discover_templates()
    if category_filter and category_filter != FILTER_ALL:
        templates = [
            item
            for item in templates
            if str(item[1].get("category") or "General") == category_filter
        ]

    if not templates:
        return []

    random.shuffle(templates)
    selected = templates[: min(limit, len(templates), MAX_PROMPTS)]

    ideas: List[PromptIdea] = []
    for idx, (path, data) in enumerate(selected, start=1):
        name = data.get("name") or path.stem
        description = data.get("description") or "Adversarial LLM test technique"
        repo = _repo_label(data, path)
        category = str(data.get("category") or "General")

        rendered = _render_template_value(str(data.get("value", "")), context)
        if team_mode == "purple":
            rendered = (
                f"[Engagement: Purple Team | Scope: authorized assessment]\n"
                f"{rendered}\n\n"
                f"{PURPLE_TEAM_NOTE}"
            )

        ideas.append(
            PromptIdea(
                index=idx,
                name=str(name),
                source=str(data.get("source") or path.name),
                repository=repo,
                technique=str(description),
                category=category,
                text=rendered,
            )
        )

    return ideas


def format_prompt_output(ideas: List[PromptIdea], team_mode: TeamMode = "red") -> str:
    if not ideas:
        return "No prompts matched your filter. Try 'All Categories' or a different target."

    mode_label = "Red Team" if team_mode == "red" else "Purple Team"
    lines: List[str] = [f"=== {mode_label} Prompt Pack ({len(ideas)} tests) ===", ""]
    for idea in ideas:
        lines.append(f"--- Prompt {idea.index} of {len(ideas)} ---")
        lines.append(f"Technique: {idea.name}")
        lines.append(f"Category: {idea.category}")
        lines.append(f"Reference: {idea.repository}")
        lines.append(f"Pattern: {idea.technique}")
        lines.append("")
        lines.append(idea.text)
        lines.append("")
    return "\n".join(lines).strip()


def _library_sync_hint() -> str:
    meta = load_update_meta()
    if not meta:
        return ""
    source = meta.get("source") or "unknown"
    version = meta.get("version") or "?"
    return f" | Library: {source} v{version}"


def engine_status(team_mode: TeamMode = "red", category_filter: str = FILTER_ALL) -> str:
    templates = _discover_templates()
    mode = "Red Team" if team_mode == "red" else "Purple Team"
    filt = f" | Filter: {category_filter}" if category_filter != FILTER_ALL else ""
    return (
        f"{mode} mode | {len(templates)} techniques | Prompts: maximum= {MAX_PROMPTS}"
        f"{filt}{_library_sync_hint()} | Standalone library"
    )
