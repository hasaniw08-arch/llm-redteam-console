"""Scroll and random-input stress test for LLM Red Team Workbench."""

from __future__ import annotations

import html
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from prompt_engine import (
    FILTER_ALL,
    generate_prompt_ideas,
    list_category_filters,
)

TeamMode = str

RANDOM_CONTEXTS = [
    "GPT-4 customer support bot with RAG over internal wiki",
    "Claude-based code assistant with file system tools",
    "Gemini chatbot for healthcare triage (authorized lab)",
    "LLama 3 agent with SQL database read access",
    "Copilot plugin with OAuth token in system prompt",
    "Multi-agent orchestrator with email send capability",
    "Document summarization pipeline with PII redaction bypass test",
    "Financial advisory LLM with portfolio API integration",
    "Internal HR chatbot with employee records retrieval",
    "Legal contract review assistant with clause extraction",
    "E-commerce recommendation engine with user profile access",
    "DevOps runbook bot with kubectl exec permissions",
    "Education tutor bot with exam answer leakage probe",
    "Insurance claims adjuster LLM with policy database",
    "Travel booking agent with payment card handling",
    "Social media moderation classifier bypass assessment",
    "Voice assistant with smart home device control",
    "Recruiting screen bot with resume PII extraction test",
    "Pharmacy interaction checker with prescription data",
    "Municipal services chatbot with citizen record lookup",
    "Banking FAQ bot with account balance tool invocation",
    "Cybersecurity SOC copilot with SIEM query tools",
    "Real estate listing generator with owner contact scrape",
    "Supply chain logistics optimizer with vendor API keys",
    "Telehealth symptom checker with diagnosis boundary test",
    "News summarizer with paywall content exfil probe",
    "Game NPC dialogue system with moderation filter test",
    "IoT firmware assistant with device credential exposure",
    "Tax preparation helper with SSN handling scope",
    "Warehouse inventory bot with supplier pricing data",
]

MODES: list[TeamMode] = ["red", "purple"]


@dataclass
class RandomInputCase:
    index: int
    team_mode: TeamMode
    category_filter: str
    context: str
    prompts_generated: int


@dataclass
class ScrollMetrics:
    viewport_width: int
    viewport_height: int
    content_width: int
    content_height: int
    scroll_required: bool
    scrollbar_visible: bool
    top_fraction: float
    bottom_fraction: float
    scroll_range_ok: bool


@dataclass
class ScrollStressReport:
    seed: int
    cases: list[RandomInputCase]
    scroll: ScrollMetrics

    @property
    def total_prompts(self) -> int:
        return sum(case.prompts_generated for case in self.cases)

    @property
    def avg_prompts(self) -> float:
        if not self.cases:
            return 0.0
        return self.total_prompts / len(self.cases)


def generate_random_cases(count: int = 100, seed: int | None = None) -> list[tuple[str, str, str]]:
    rng = random.Random(seed)
    categories = list_category_filters()
    pairs: list[tuple[str, str, str]] = []
    for _ in range(count):
        mode = rng.choice(MODES)
        category = rng.choice(categories)
        context = rng.choice(RANDOM_CONTEXTS)
        if rng.random() < 0.35:
            context = f"{context} — engagement #{rng.randint(1000, 9999)} scope OWASP LLM0{rng.randint(1, 9)}"
        pairs.append((mode, category, context))
    return pairs


def run_random_input_cases(count: int = 100, seed: int | None = None) -> list[RandomInputCase]:
    rng_seed = seed if seed is not None else random.randint(1, 999_999)
    results: list[RandomInputCase] = []
    for index, (mode, category, context) in enumerate(generate_random_cases(count, rng_seed), start=1):
        ideas = generate_prompt_ideas(
            context,
            team_mode=mode,  # type: ignore[arg-type]
            category_filter=category,
        )
        results.append(
            RandomInputCase(
                index=index,
                team_mode=mode,
                category_filter=category,
                context=context,
                prompts_generated=len(ideas),
            )
        )
    return results


def measure_scroll_metrics(window_width: int = 820, window_height: int = 560) -> ScrollMetrics:
    import tkinter as tk

    from main import SaaSApp

    root = SaaSApp()
    root.geometry(f"{window_width}x{window_height}")
    root.update_idletasks()
    root.update()

    canvas = root._scroll_canvas
    region = canvas.bbox("all") or (0, 0, 0, 0)
    content_w = max(0, int(region[2] - region[0]))
    content_h = max(0, int(region[3] - region[1]))
    view_w = canvas.winfo_width()
    view_h = canvas.winfo_height()

    scroll_required = content_h > view_h + 2
    scrollbar = root._scroll_bar
    scrollbar_visible = scrollbar.winfo_ismapped() == 1

    canvas.yview_moveto(0.0)
    root.update_idletasks()
    top_fraction = canvas.yview()[0]

    canvas.yview_moveto(1.0)
    root.update_idletasks()
    bottom_fraction = canvas.yview()[0]

    scroll_range_ok = (bottom_fraction > top_fraction) if scroll_required else True

    root.destroy()
    tk._default_root = None  # type: ignore[attr-defined]

    return ScrollMetrics(
        viewport_width=view_w,
        viewport_height=view_h,
        content_width=content_w,
        content_height=content_h,
        scroll_required=scroll_required,
        scrollbar_visible=scrollbar_visible,
        top_fraction=top_fraction,
        bottom_fraction=bottom_fraction,
        scroll_range_ok=scroll_range_ok,
    )


def run_scroll_stress_test(count: int = 100, seed: int | None = None) -> ScrollStressReport:
    rng_seed = seed if seed is not None else random.randint(1, 999_999)
    cases = run_random_input_cases(count=count, seed=rng_seed)
    scroll = measure_scroll_metrics()
    return ScrollStressReport(seed=rng_seed, cases=cases, scroll=scroll)


def _e(text: str) -> str:
    return html.escape(text, quote=True)


def render_html_report(report: ScrollStressReport) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    scroll = report.scroll
    pass_scroll = scroll.scroll_required and scroll.scrollbar_visible and scroll.scroll_range_ok
    verdict = "PASS" if pass_scroll else "REVIEW"
    verdict_color = "#1f8a5b" if pass_scroll else "#c0392b"

    rows = []
    for case in report.cases[:25]:
        rows.append(
            f"<tr><td>{case.index:03d}</td><td>{_e(case.team_mode)}</td>"
            f"<td>{_e(case.category_filter)}</td><td>{case.prompts_generated}</td>"
            f"<td>{_e(case.context[:72])}...</td></tr>"
        )
    if len(report.cases) > 25:
        rows.append(
            f'<tr><td colspan="5" class="muted">… {len(report.cases) - 25} more cases omitted …</td></tr>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Scroll Stress Test — {len(report.cases)} Random Inputs</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; background: #f4f6fb; color: #1b2a41; margin: 0; }}
    .hero {{ background: linear-gradient(135deg, #6b21a8, #9333ea); color: #fff; padding: 36px 24px; }}
    .container {{ max-width: 980px; margin: -20px auto 40px; padding: 0 20px; }}
    .card {{ background: #fff; border-radius: 16px; padding: 22px; margin-bottom: 18px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }}
    .stat {{ background: #f8f4ff; border-radius: 12px; padding: 14px; text-align: center; }}
    .num {{ display: block; font-size: 1.6rem; font-weight: 700; color: #6b21a8; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th, td {{ border-bottom: 1px solid #e5e7ef; padding: 8px; text-align: left; vertical-align: top; }}
    .verdict {{ font-size: 1.4rem; font-weight: 700; color: {verdict_color}; }}
    .muted {{ color: #5b6b82; }}
  </style>
</head>
<body>
  <header class="hero">
    <h1>Scroll Bar Stress Test</h1>
    <p>{len(report.cases)} random inputs · laptop viewport 820×560 · seed {_e(str(report.seed))}</p>
    <p>{generated}</p>
  </header>
  <main class="container">
    <section class="card">
      <p class="verdict">Scroll test: {verdict}</p>
      <div class="stats">
        <div class="stat"><span class="num">{len(report.cases)}</span>Random inputs</div>
        <div class="stat"><span class="num">{report.total_prompts}</span>Total prompts</div>
        <div class="stat"><span class="num">{report.avg_prompts:.1f}</span>Avg prompts / input</div>
        <div class="stat"><span class="num">{scroll.content_height}px</span>Content height</div>
        <div class="stat"><span class="num">{scroll.viewport_height}px</span>Viewport height</div>
      </div>
      <p class="muted" style="margin-top:16px">
        Scroll required: {scroll.scroll_required} · Scrollbar visible: {scroll.scrollbar_visible} ·
        Range OK (top={scroll.top_fraction:.3f}, bottom={scroll.bottom_fraction:.3f})
      </p>
    </section>
    <section class="card">
      <h2>Sample cases (first 25)</h2>
      <table>
        <thead><tr><th>#</th><th>Mode</th><th>Filter</th><th>Prompts</th><th>Context</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </section>
  </main>
</body>
</html>"""


def write_report(path: Path, report: ScrollStressReport) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html_report(report), encoding="utf-8")
    return path
