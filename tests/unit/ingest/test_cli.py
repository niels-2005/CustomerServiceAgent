from __future__ import annotations

import pytest

from customer_bot.retrieval.ingestion import CorpusValidationError, IngestResult


def test_build_parser_defaults_to_faq_source() -> None:
    from customer_bot.ingest.cli import build_parser

    args = build_parser().parse_args([])

    assert args.source == "faq"
    assert args.path is None


def test_cli_exits_with_code_2_for_corpus_validation_error(monkeypatch, capsys) -> None:
    from customer_bot.ingest.cli import main

    class FakeService:
        def ingest(self, **kwargs):
            del kwargs
            raise CorpusValidationError("bad csv")

    monkeypatch.setattr("customer_bot.ingest.cli.get_settings", lambda: object())
    monkeypatch.setattr("customer_bot.ingest.cli.IngestionService", lambda settings: FakeService())
    monkeypatch.setattr("sys.argv", ["customer-bot-ingest"])

    with pytest.raises(SystemExit, match="2"):
        main()

    captured = capsys.readouterr()
    assert "Ingestion failed: bad csv" in captured.err


def test_cli_exits_with_code_1_for_unexpected_error(monkeypatch, capsys) -> None:
    from customer_bot.ingest.cli import main

    class FakeService:
        def ingest(self, **kwargs):
            del kwargs
            raise RuntimeError("backend down")

    monkeypatch.setattr("customer_bot.ingest.cli.get_settings", lambda: object())
    monkeypatch.setattr("customer_bot.ingest.cli.IngestionService", lambda settings: FakeService())
    monkeypatch.setattr("sys.argv", ["customer-bot-ingest", "--source", "products"])

    with pytest.raises(SystemExit, match="1"):
        main()

    captured = capsys.readouterr()
    assert "Ingestion failed unexpectedly: backend down" in captured.err


def test_cli_prints_success_summary(monkeypatch, capsys) -> None:
    from customer_bot.ingest.cli import main

    class FakeService:
        def ingest(self, **kwargs):
            assert kwargs == {"source": "products", "corpus_path": None}
            return IngestResult(records_ingested=4, collection_name="products")

    monkeypatch.setattr("customer_bot.ingest.cli.get_settings", lambda: object())
    monkeypatch.setattr("customer_bot.ingest.cli.IngestionService", lambda settings: FakeService())
    monkeypatch.setattr("sys.argv", ["customer-bot-ingest", "--source", "products"])

    main()

    captured = capsys.readouterr()
    assert "Ingestion completed successfully (collection=products, records=4)." in captured.out
