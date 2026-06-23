"""Download library updates: LAN feed first, then GitHub fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from config import load_config, update_meta_path, user_data_dir
from network_info import NetworkSnapshot, collect_network_info


@dataclass
class UpdateResult:
    ok: bool
    source: str = ""
    message: str = ""
    files_updated: int = 0
    version: str = ""


def load_update_meta() -> dict[str, Any] | None:
    path = update_meta_path()
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _http_get(url: str, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": "LLMRedTeamConsole/1.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _feed_base_url(feed_url: str) -> str:
    cleaned = feed_url.strip().rstrip("/")
    if cleaned.lower().endswith("feed.json"):
        return cleaned[: -len("feed.json")].rstrip("/")
    return cleaned


def _file_download_url(base_url: str, relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/").lstrip("/")
    return urljoin(f"{base_url.rstrip('/')}/", normalized)


def _try_source(source_name: str, feed_url: str, timeout: int) -> UpdateResult:
    if not feed_url.strip():
        return UpdateResult(False, source=source_name, message="Feed URL not configured.")

    try:
        manifest_text = _http_get(feed_url.strip(), timeout)
        manifest = json.loads(manifest_text)
    except HTTPError as exc:
        return UpdateResult(False, source=source_name, message=f"HTTP {exc.code} fetching feed.")
    except URLError as exc:
        return UpdateResult(False, source=source_name, message=f"Network error: {exc.reason}")
    except json.JSONDecodeError:
        return UpdateResult(False, source=source_name, message="Feed JSON is invalid.")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return UpdateResult(False, source=source_name, message="Feed has no files list.")

    base_url = _feed_base_url(feed_url)
    target_root = user_data_dir()
    updated = 0

    for item in files:
        rel_path = str(item).strip()
        if not rel_path or ".." in rel_path.replace("\\", "/"):
            continue
        try:
            content = _http_get(_file_download_url(base_url, rel_path), timeout)
        except (HTTPError, URLError) as exc:
            detail = getattr(exc, "reason", None) or getattr(exc, "code", exc)
            return UpdateResult(
                False,
                source=source_name,
                message=f"Failed to download {rel_path}: {detail}",
                files_updated=updated,
            )

        dest = target_root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        updated += 1

    version = str(manifest.get("version") or "unknown")
    meta = {
        "source": source_name,
        "version": version,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "feed_url": feed_url.strip(),
        "files_updated": updated,
    }
    with update_meta_path().open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)

    return UpdateResult(
        ok=True,
        source=source_name,
        message=f"Updated {updated} file(s) from {source_name} (v{version}).",
        files_updated=updated,
        version=version,
    )


def update_library(
    config: dict | None = None,
    network: NetworkSnapshot | None = None,
) -> UpdateResult:
    cfg = config or load_config()
    timeout = int(cfg.get("update_timeout_seconds", 20))
    lan_url = str(cfg.get("lan_feed_url") or "").strip()
    github_url = str(cfg.get("github_feed_url") or "").strip()
    snap = network or collect_network_info()
    errors: list[str] = []

    if lan_url:
        lan_result = _try_source("LAN", lan_url, timeout)
        if lan_result.ok:
            return lan_result
        errors.append(lan_result.message)

    if not snap.internet_ok:
        hint = (
            "Offline — set lan_feed_url in config.local.json for LAN updates, "
            "or connect via Wi‑Fi/Ethernet for GitHub fallback."
        )
        if errors:
            return UpdateResult(False, message=f"{errors[0]} {hint}")
        return UpdateResult(False, message=hint)

    if github_url:
        github_result = _try_source("GitHub", github_url, timeout)
        if github_result.ok:
            return github_result
        errors.append(github_result.message)

    if errors:
        return UpdateResult(False, message=" | ".join(errors))
    return UpdateResult(False, message="No update feed URLs configured.")
