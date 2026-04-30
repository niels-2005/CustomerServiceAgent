"""CLI entrypoint for corpus ingestion into the vector store."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from customer_bot.config import get_settings
from customer_bot.retrieval.ingestion import CorpusValidationError, IngestionService


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for FAQ and product ingestion."""
    parser = argparse.ArgumentParser(
        description=(
            "Ingest FAQ or product CSV data into the configured Chroma vector store backend."
        )
    )
    parser.add_argument(
        "--source",
        choices=("faq", "products"),
        default="faq",
        help="Knowledge source to ingest. Defaults to faq.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help=(
            "Optional override for the source CSV path. Defaults to the path "
            "configured for the selected source."
        ),
    )
    return parser


def main() -> None:
    """Run ingestion and map common failures to stable exit codes."""
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    service = IngestionService(settings=settings)

    try:
        result = service.ingest(source=args.source, corpus_path=args.path)
    except CorpusValidationError as exc:
        # Exit code 2 represents invalid user-supplied corpus input.
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except Exception as exc:
        # Exit code 1 represents unexpected runtime or infrastructure failures.
        print(f"Ingestion failed unexpectedly: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        "Ingestion completed successfully "
        f"(collection={result.collection_name}, records={result.records_ingested})."
    )
