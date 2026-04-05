from __future__ import annotations

import argparse
import sys
from pathlib import Path

from customer_bot.config import get_settings
from customer_bot.retrieval.ingestion import CorpusValidationError, IngestionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest FAQ corpus CSV into Chroma vector store.")
    parser.add_argument(
        "--corpus-path",
        type=Path,
        default=None,
        help="Optional override for corpus CSV path. Defaults to settings corpus_csv_path.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    service = IngestionService(settings=settings)

    try:
        result = service.ingest(corpus_path=args.corpus_path)
    except CorpusValidationError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except Exception as exc:
        print(f"Ingestion failed unexpectedly: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        "Ingestion completed successfully "
        f"(collection={result.collection_name}, records={result.records_ingested})."
    )
