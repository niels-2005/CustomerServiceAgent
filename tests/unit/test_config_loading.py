from __future__ import annotations

from pathlib import Path

from customer_bot.config import Settings


def test_settings_load_yaml_defaults(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.delenv("FAQ_RETRIEVAL_TOP_K", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.llm_provider == "ollama"
    assert settings.embedding_provider == "ollama"
    assert settings.faq_retrieval_top_k == 3
    assert settings.products_retrieval_top_k == 3
    assert settings.products_corpus_csv_path == Path("dataset/products.csv")
    assert settings.products_collection_name == "customer_bot_products"
    assert settings.products_similarity_cutoff == 0.7
    assert settings.guardrails_presidio_config_path == Path(
        "src/customer_bot/config/presidio_config.yaml"
    )
    assert "konto" in settings.guardrails_topic_allowed_domain_hints
    assert "alle frauen" in settings.guardrails_bias_terms
    assert settings.openai_api_key == ""


def test_env_overrides_yaml_defaults(monkeypatch) -> None:
    monkeypatch.setenv("API_PORT", "9100")
    monkeypatch.setenv("FAQ_RETRIEVAL_TOP_K", "7")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("PRODUCTS_CORPUS_CSV_PATH", "dataset/custom-products.csv")
    monkeypatch.setenv("PRODUCTS_SIMILARITY_CUTOFF", "0.82")

    settings = Settings(_env_file=None)

    assert settings.api_port == 9100
    assert settings.faq_retrieval_top_k == 7
    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.products_corpus_csv_path == Path("dataset/custom-products.csv")
    assert settings.products_similarity_cutoff == 0.82
