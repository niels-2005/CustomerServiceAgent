from __future__ import annotations

import math
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langfuse import Langfuse

from customer_bot.config import Settings


def timestamp_slug() -> str:
    """Return a lexically sortable UTC timestamp for benchmark artifacts."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M")


def prepare_report_directories(artifacts_root: Path) -> tuple[str, Path, Path]:
    """Allocate a unique history directory plus a stable latest directory."""
    base_slug = timestamp_slug()
    history_root = artifacts_root / "history"
    latest_root = artifacts_root / "latest"
    history_root.mkdir(parents=True, exist_ok=True)

    suffix = 0
    while True:
        run_slug = base_slug if suffix == 0 else f"{base_slug}-{suffix:02d}"
        report_dir = history_root / run_slug
        if not report_dir.exists():
            return run_slug, report_dir, latest_root
        suffix += 1


def publish_latest_report(report_dir: Path, latest_root: Path) -> None:
    """Refresh the latest benchmark summary files after a completed run."""
    latest_root.mkdir(parents=True, exist_ok=True)
    for filename in ("summary.json", "summary.md"):
        shutil.copy2(report_dir / filename, latest_root / filename)


def resolve_runtime_session_id(run_slug: str, session_id: str | None) -> str | None:
    """Namespace non-empty benchmark sessions so repeated runs stay isolated in Redis."""
    if session_id is None:
        return None
    return f"{run_slug}__{session_id}"


def ms_to_seconds(value_ms: float | None) -> float | None:
    """Convert milliseconds to rounded seconds for human-facing reports."""
    if value_ms is None:
        return None
    return round(value_ms / 1000, 3)


def format_seconds(value_ms: float | None) -> str:
    """Render benchmark latency values as seconds."""
    value_seconds = ms_to_seconds(value_ms)
    if value_seconds is None:
        return "unavailable"
    return f"{value_seconds:.3f} s"


def format_currency(value: float | None) -> str:
    """Render benchmark cost values as euros."""
    if value is None:
        return "unavailable"
    return f"{value:.6f} €"


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Render a compact Markdown table for benchmark summaries."""
    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_rows = ["| " + " | ".join(row) + " |" for row in rows]
    return [header_row, separator_row, *body_rows]


def percentile(values: list[float], percentile_value: int) -> float | None:
    """Return a simple percentile using ceiling rank for small benchmark sets."""
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil((percentile_value / 100) * len(ordered))
    index = max(rank - 1, 0)
    return ordered[index]


def create_langfuse_client(settings: Settings) -> Langfuse | None:
    """Create a Langfuse client only when benchmark credentials are configured."""
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse.host,
    )


def compact_json(value: Any) -> str:
    """Render nested values compactly for reports and prompts."""
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
