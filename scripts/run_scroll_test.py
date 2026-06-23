"""Run scroll bar stress test with 100 random prompt inputs."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scroll_stress_test import run_scroll_stress_test, write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Red Team scroll + random input stress test")
    parser.add_argument("--count", type=int, default=100, help="Number of random inputs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-open", action="store_true", help="Do not open HTML report")
    args = parser.parse_args()

    print(f"Running scroll stress test ({args.count} random inputs, seed={args.seed})...")
    report = run_scroll_stress_test(count=args.count, seed=args.seed)

    out_dir = Path.home() / "Downloads" / "LLM-RedTeam-Reports"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"scroll-test-{args.count}-{stamp}.html"
    write_report(out_path, report)

    scroll = report.scroll
    pass_scroll = scroll.scroll_required and scroll.scrollbar_visible and scroll.scroll_range_ok
    verdict = "PASS" if pass_scroll else "REVIEW"

    print("")
    print("=== Scroll Bar Stress Test ===")
    print(f"  Random inputs:     {len(report.cases)}")
    print(f"  Total prompts:     {report.total_prompts}")
    print(f"  Avg prompts/input: {report.avg_prompts:.1f}")
    print(f"  Viewport:          {scroll.viewport_width}x{scroll.viewport_height}px")
    print(f"  Content height:    {scroll.content_height}px")
    print(f"  Scroll required:   {scroll.scroll_required}")
    print(f"  Scrollbar visible: {scroll.scrollbar_visible}")
    print(f"  Scroll range OK:   {scroll.scroll_range_ok}")
    print(f"  Verdict:           {verdict}")
    print(f"  Report saved:      {out_path}")

    if not args.no_open:
        webbrowser.open(out_path.as_uri())


if __name__ == "__main__":
    main()
