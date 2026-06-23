"""App paths and optional update feed settings."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_GITHUB_FEED_URL = (
    "https://raw.githubusercontent.com/hasaniw08-arch/llm-redteam-console/main/data/feed.json"
)

DEFAULT_CONFIG = {
    "lan_feed_url": "",
    "github_feed_url": DEFAULT_GITHUB_FEED_URL,
    "allow_lan_only_updates": True,
    "update_timeout_seconds": 20,
}


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _bundle_roots() -> list[Path]:
    if getattr(sys, "frozen", False):
        roots: list[Path] = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
        exe_dir = Path(sys.executable).resolve().parent
        roots.extend([exe_dir, exe_dir / "_internal"])
        return roots
    return [Path(__file__).resolve().parent]


def bundled_data_dir() -> Path:
    for root in _bundle_roots():
        candidate = root / "data"
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parent / "data"


def user_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        folder = app_root() / "data"
    else:
        folder = Path.home() / "AppData" / "Local" / "LLMRedTeamConsole" / "data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def config_path() -> Path:
    return app_root() / "config.local.json"


def update_meta_path() -> Path:
    return user_data_dir() / "update_meta.json"


def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    path = config_path()
    if path.is_file():
        with path.open(encoding="utf-8") as handle:
            stored = json.load(handle)
        config.update(stored)
    config["lan_feed_url"] = os.environ.get("LLM_LAN_FEED_URL", config.get("lan_feed_url", ""))
    config["github_feed_url"] = os.environ.get(
        "LLM_GITHUB_FEED_URL",
        config.get("github_feed_url", DEFAULT_GITHUB_FEED_URL),
    )
    return config


def save_config(config: dict) -> None:
    payload = {
        "lan_feed_url": config.get("lan_feed_url", ""),
        "github_feed_url": config.get("github_feed_url", DEFAULT_GITHUB_FEED_URL),
        "allow_lan_only_updates": bool(config.get("allow_lan_only_updates", True)),
        "update_timeout_seconds": int(config.get("update_timeout_seconds", 20)),
    }
    with config_path().open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
