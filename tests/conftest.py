from __future__ import annotations

from pathlib import Path

import pytest
from limits.storage import storage_from_string as build_rate_limit_storage

from customer_bot.api.deps import clear_dependency_caches
from customer_bot.config import Settings


@pytest.fixture(autouse=True)
def _clear_di_caches() -> None:
    clear_dependency_caches()


@pytest.fixture(autouse=True)
def _stub_rate_limit_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "customer_bot.api.rate_limit.storage_from_string",
        lambda uri, **kwargs: build_rate_limit_storage("memory://"),
    )


@pytest.fixture
def settings_factory(tmp_path: Path):
    flat_paths = {
        "api_host": ("api", "host"),
        "api_port": ("api", "port"),
        "api_max_user_message_length": ("api", "max_user_message_length"),
        "api_cors_allow_origins": ("api", "cors_allow_origins"),
        "api_cors_allow_credentials": ("api", "cors_allow_credentials"),
        "api_cors_allow_methods": ("api", "cors_allow_methods"),
        "api_cors_allow_headers": ("api", "cors_allow_headers"),
        "api_trusted_hosts": ("api", "trusted_hosts"),
        "api_rate_limit_enabled": ("api", "rate_limit", "enabled"),
        "api_rate_limit_default_limit": ("api", "rate_limit", "default_limit"),
        "api_rate_limit_chat_limit": ("api", "rate_limit", "chat_limit"),
        "api_rate_limit_headers_enabled": ("api", "rate_limit", "headers_enabled"),
        "api_rate_limit_storage_uri": ("api", "rate_limit", "storage_uri"),
        "api_rate_limit_key_prefix": ("api", "rate_limit", "key_prefix"),
        "api_rate_limit_trust_proxy_headers": ("api", "rate_limit", "trust_proxy_headers"),
        "llm_provider": ("selectors", "llm"),
        "embedding_provider": ("selectors", "embedding"),
        "guardrail_provider": ("selectors", "guardrail"),
        "ollama_base_url": ("llm", "ollama", "base_url"),
        "ollama_chat_model": ("llm", "ollama", "chat_model"),
        "ollama_temperature": ("llm", "ollama", "temperature"),
        "ollama_request_timeout_seconds": ("llm", "ollama", "request_timeout_seconds"),
        "ollama_prompt_key": ("llm", "ollama", "prompt_key"),
        "ollama_json_mode": ("llm", "ollama", "json_mode"),
        "ollama_thinking": ("llm", "ollama", "thinking"),
        "ollama_context_window": ("llm", "ollama", "context_window"),
        "ollama_keep_alive": ("llm", "ollama", "keep_alive"),
        "ollama_embedding_model": ("embedding", "ollama", "model"),
        "ollama_embedding_batch_size": ("embedding", "ollama", "batch_size"),
        "ollama_embedding_keep_alive": ("embedding", "ollama", "keep_alive"),
        "ollama_embedding_query_instruction": ("embedding", "ollama", "query_instruction"),
        "ollama_embedding_text_instruction": ("embedding", "ollama", "text_instruction"),
        "ollama_embedding_num_ctx": ("embedding", "ollama", "num_ctx"),
        "openai_llm_model": ("llm", "openai", "model"),
        "openai_llm_temperature": ("llm", "openai", "temperature"),
        "openai_llm_max_completion_tokens": ("llm", "openai", "max_completion_tokens"),
        "openai_llm_max_retries": ("llm", "openai", "max_retries"),
        "openai_llm_timeout_seconds": ("llm", "openai", "timeout_seconds"),
        "openai_llm_api_base": ("llm", "openai", "api_base"),
        "openai_llm_api_version": ("llm", "openai", "api_version"),
        "openai_llm_strict": ("llm", "openai", "strict"),
        "openai_llm_reasoning_effort": ("llm", "openai", "reasoning_effort"),
        "openai_embedding_model": ("embedding", "openai", "model"),
        "openai_embedding_mode": ("embedding", "openai", "mode"),
        "openai_embedding_batch_size": ("embedding", "openai", "batch_size"),
        "openai_embedding_dimensions": ("embedding", "openai", "dimensions"),
        "openai_embedding_max_retries": ("embedding", "openai", "max_retries"),
        "openai_embedding_timeout_seconds": ("embedding", "openai", "timeout_seconds"),
        "openai_embedding_api_base": ("embedding", "openai", "api_base"),
        "openai_embedding_api_version": ("embedding", "openai", "api_version"),
        "openai_embedding_num_workers": ("embedding", "openai", "num_workers"),
        "openai_guardrail_model": ("guardrail", "openai", "model"),
        "openai_guardrail_temperature": ("guardrail", "openai", "temperature"),
        "openai_guardrail_max_completion_tokens": (
            "guardrail",
            "openai",
            "max_completion_tokens",
        ),
        "openai_guardrail_max_retries": ("guardrail", "openai", "max_retries"),
        "openai_guardrail_timeout_seconds": ("guardrail", "openai", "timeout_seconds"),
        "openai_guardrail_api_base": ("guardrail", "openai", "api_base"),
        "openai_guardrail_api_version": ("guardrail", "openai", "api_version"),
        "openai_guardrail_strict": ("guardrail", "openai", "strict"),
        "openai_guardrail_reasoning_effort": ("guardrail", "openai", "reasoning_effort"),
        "chroma_persist_dir": ("storage", "chroma_persist_dir"),
        "faq_collection_name": ("storage", "faq", "collection_name"),
        "products_collection_name": ("storage", "products", "collection_name"),
        "faq_corpus_csv_path": ("ingestion", "faq", "corpus_csv_path"),
        "faq_text_ingestion_mode": ("ingestion", "faq", "text_ingestion_mode"),
        "products_corpus_csv_path": ("ingestion", "products", "corpus_csv_path"),
        "faq_retrieval_top_k": ("retrieval", "faq", "top_k"),
        "faq_similarity_cutoff": ("retrieval", "faq", "similarity_cutoff"),
        "products_retrieval_top_k": ("retrieval", "products", "top_k"),
        "products_similarity_cutoff": ("retrieval", "products", "similarity_cutoff"),
        "memory_max_turns": ("memory", "max_turns"),
        "memory_session_limit_text": ("memory", "session_limit_text"),
        "memory_redis_url": ("memory", "redis", "redis_url"),
        "memory_key_prefix": ("memory", "redis", "key_prefix"),
        "memory_ttl_seconds": ("memory", "redis", "ttl_seconds"),
        "agent_description": ("agent", "agent_description"),
        "agent_system_prompt": ("agent", "agent_system_prompt"),
        "agent_timeout_seconds": ("agent", "agent_timeout_seconds"),
        "employee_request_instruction": ("messages", "employee_request_instruction"),
        "no_match_instruction": ("messages", "no_match_instruction"),
        "faq_tool_description": ("messages", "faq_tool_description"),
        "product_tool_description": ("messages", "product_tool_description"),
        "error_fallback_text": ("messages", "error_fallback_text"),
        "guardrails_enabled": ("guardrails", "global", "enabled"),
        "guardrails_fail_closed": ("guardrails", "global", "fail_closed"),
        "guardrails_max_output_retries": ("guardrails", "global", "max_output_retries"),
        "guardrails_trace_inputs": ("guardrails", "tracing", "inputs"),
        "guardrails_trace_outputs": ("guardrails", "tracing", "outputs"),
        "guardrails_trace_include_config": ("guardrails", "tracing", "include_config"),
        "guardrails_presidio_config_path": ("guardrails", "input", "pii", "presidio_config_path"),
        "guardrails_presidio_language": ("guardrails", "input", "pii", "presidio_language"),
        "guardrails_presidio_allow_list": ("guardrails", "input", "pii", "presidio_allow_list"),
        "guardrails_presidio_score_threshold": (
            "guardrails",
            "input",
            "pii",
            "presidio_score_threshold",
        ),
        "guardrails_input_pii_enabled": ("guardrails", "input", "pii", "enabled"),
        "guardrails_input_pii_entities": ("guardrails", "input", "pii", "entities"),
        "guardrails_input_pii_custom_patterns": (
            "guardrails",
            "input",
            "pii",
            "custom_patterns",
        ),
        "guardrails_input_pii_message": ("guardrails", "input", "pii", "message"),
        "guardrails_prompt_injection_enabled": (
            "guardrails",
            "input",
            "prompt_injection",
            "enabled",
        ),
        "guardrails_prompt_injection_system_prompt": (
            "guardrails",
            "input",
            "prompt_injection",
            "system_prompt",
        ),
        "guardrails_prompt_injection_user_prompt_template": (
            "guardrails",
            "input",
            "prompt_injection",
            "user_prompt_template",
        ),
        "guardrails_prompt_injection_message": (
            "guardrails",
            "input",
            "prompt_injection",
            "message",
        ),
        "guardrails_prompt_injection_heuristic_terms": (
            "guardrails",
            "input",
            "prompt_injection",
            "heuristic_terms",
        ),
        "guardrails_topic_relevance_enabled": (
            "guardrails",
            "input",
            "topic_relevance",
            "enabled",
        ),
        "guardrails_topic_relevance_system_prompt": (
            "guardrails",
            "input",
            "topic_relevance",
            "system_prompt",
        ),
        "guardrails_topic_relevance_user_prompt_template": (
            "guardrails",
            "input",
            "topic_relevance",
            "user_prompt_template",
        ),
        "guardrails_topic_relevance_message": (
            "guardrails",
            "input",
            "topic_relevance",
            "message",
        ),
        "guardrails_topic_relevance_help_text": (
            "guardrails",
            "input",
            "topic_relevance",
            "help_text",
        ),
        "guardrails_topic_allowed_domain_hints": (
            "guardrails",
            "input",
            "topic_relevance",
            "allowed_domain_hints",
        ),
        "guardrails_escalation_enabled": ("guardrails", "input", "escalation", "enabled"),
        "guardrails_escalation_system_prompt": (
            "guardrails",
            "input",
            "escalation",
            "system_prompt",
        ),
        "guardrails_escalation_user_prompt_template": (
            "guardrails",
            "input",
            "escalation",
            "user_prompt_template",
        ),
        "guardrails_escalation_message": ("guardrails", "input", "escalation", "message"),
        "guardrails_escalation_heuristic_terms": (
            "guardrails",
            "input",
            "escalation",
            "heuristic_terms",
        ),
        "guardrails_output_pii_enabled": ("guardrails", "output", "pii", "enabled"),
        "guardrails_output_pii_entities": ("guardrails", "output", "pii", "entities"),
        "guardrails_output_pii_custom_patterns": (
            "guardrails",
            "output",
            "pii",
            "custom_patterns",
        ),
        "guardrails_grounding_enabled": ("guardrails", "output", "grounding", "enabled"),
        "guardrails_grounding_system_prompt": (
            "guardrails",
            "output",
            "grounding",
            "system_prompt",
        ),
        "guardrails_grounding_user_prompt_template": (
            "guardrails",
            "output",
            "grounding",
            "user_prompt_template",
        ),
        "guardrails_bias_enabled": ("guardrails", "output", "bias", "enabled"),
        "guardrails_bias_system_prompt": ("guardrails", "output", "bias", "system_prompt"),
        "guardrails_bias_user_prompt_template": (
            "guardrails",
            "output",
            "bias",
            "user_prompt_template",
        ),
        "guardrails_bias_terms": ("guardrails", "output", "bias", "bias_terms"),
        "guardrails_rewrite_enabled": ("guardrails", "output", "rewrite", "enabled"),
        "guardrails_rewrite_system_prompt": (
            "guardrails",
            "output",
            "rewrite",
            "system_prompt",
        ),
        "guardrails_rewrite_user_prompt_template": (
            "guardrails",
            "output",
            "rewrite",
            "user_prompt_template",
        ),
        "langfuse_fail_fast": ("langfuse", "fail_fast"),
        "langfuse_host": ("langfuse", "host"),
        "langfuse_tracing_environment": ("langfuse", "tracing_environment"),
        "langfuse_release": ("langfuse", "release"),
    }

    def _set_nested_value(payload: dict[str, object], path: tuple[str, ...], value: object) -> None:
        current = payload
        for key in path[:-1]:
            current = current.setdefault(key, {})  # type: ignore[assignment]
        current[path[-1]] = value

    def _build(**overrides: object) -> Settings:
        (tmp_path / "presidio_config.yaml").write_text(
            "supported_languages:\n  - de\nnlp_engine_name: spacy\nmodels: []\n",
            encoding="utf-8",
        )
        base_data: dict[str, object] = {
            "api": {
                "host": "127.0.0.1",
                "port": 9000,
                "max_user_message_length": 500,
                "cors_allow_origins": [
                    "http://127.0.0.1:3000",
                    "http://localhost:3000",
                    "http://127.0.0.1:5173",
                    "http://localhost:5173",
                ],
                "cors_allow_credentials": False,
                "cors_allow_methods": ["GET", "POST"],
                "cors_allow_headers": ["Content-Type", "X-Request-ID"],
                "trusted_hosts": ["127.0.0.1", "localhost", "testserver"],
                "rate_limit": {
                    "enabled": True,
                    "default_limit": "60/minute",
                    "chat_limit": "10/minute",
                    "headers_enabled": True,
                    "storage_uri": "redis://:testsecret@127.0.0.1:6379/1",
                    "key_prefix": "customer-bot:test:ratelimit",
                    "trust_proxy_headers": False,
                },
            },
            "selectors": {
                "llm": "ollama",
                "embedding": "ollama",
                "guardrail": "openai",
            },
            "OPENAI_API_KEY": "sk-test-openai",
            "llm": {
                "ollama": {
                    "chat_model": "qwen3.5:2b",
                    "base_url": None,
                    "request_timeout_seconds": None,
                    "thinking": None,
                    "context_window": None,
                    "temperature": None,
                    "prompt_key": None,
                    "json_mode": None,
                    "keep_alive": "",
                },
                "openai": {
                    "model": "gpt-4o-mini",
                    "temperature": None,
                    "max_completion_tokens": None,
                    "max_retries": None,
                    "timeout_seconds": None,
                    "api_base": None,
                    "api_version": None,
                    "strict": None,
                    "reasoning_effort": None,
                },
            },
            "embedding": {
                "ollama": {
                    "model": "qwen3-embedding:0.6b",
                    "batch_size": None,
                    "keep_alive": None,
                    "query_instruction": None,
                    "text_instruction": None,
                    "num_ctx": 2048,
                },
                "openai": {
                    "model": "text-embedding-3-small",
                    "mode": None,
                    "batch_size": None,
                    "dimensions": None,
                    "max_retries": None,
                    "timeout_seconds": None,
                    "api_base": None,
                    "api_version": None,
                    "num_workers": None,
                },
            },
            "guardrail": {
                "openai": {
                    "model": "gpt-4o-mini",
                    "temperature": 0,
                    "max_completion_tokens": 256,
                    "max_retries": None,
                    "timeout_seconds": None,
                    "api_base": None,
                    "api_version": None,
                    "strict": None,
                    "reasoning_effort": "none",
                }
            },
            "storage": {
                "chroma_persist_dir": tmp_path / "chroma",
                "faq": {"collection_name": "test_collection"},
                "products": {"collection_name": "test_products_collection"},
            },
            "ingestion": {
                "faq": {
                    "corpus_csv_path": tmp_path / "corpus.csv",
                    "text_ingestion_mode": "question_only",
                },
                "products": {"corpus_csv_path": tmp_path / "products.csv"},
            },
            "retrieval": {
                "faq": {"top_k": 3, "similarity_cutoff": 0.60},
                "products": {"top_k": 3, "similarity_cutoff": 0.70},
            },
            "memory": {
                "max_turns": 20,
                "session_limit_text": "Bitte starte eine neue Session.",
                "redis": {
                    "redis_url": "redis://:testsecret@127.0.0.1:6379/2",
                    "key_prefix": "customer-bot:test:memory",
                    "ttl_seconds": 86400,
                },
            },
            "agent": {
                "agent_description": "Agent for FAQ and product responses",
                "agent_system_prompt": (
                    "You are a customer support assistant. "
                    "Use the faq_lookup tool for FAQ information. "
                    "Use the product_lookup tool for product information. "
                    "You may answer a follow-up without calling the tool only when "
                    "the needed information is already grounded in the chat history. "
                    "The tool returns JSON with `matches`, where each item has "
                    "grounded fields for that tool. "
                    "Write a concise German answer using only information grounded "
                    "in tool results or prior chat history grounded in those results. "
                    "Do not invent product details, policies, or guarantees."
                ),
                "agent_timeout_seconds": 45.0,
            },
            "messages": {
                "employee_request_instruction": (
                    "If the user asks for a human agent before a guardrail handoff, "
                    "use one short German reply that stays close to the pattern "
                    "'Before I pass you to a human advisor, maybe I can help? I can "
                    "answer questions about products, orders, shipping, returns, "
                    "payments, privacy, or support processes. What is it about?', do "
                    "not promise handoff, do not claim that handoff is impossible, "
                    "and do not ask for order numbers, customer numbers, or contact details."
                ),
                "no_match_instruction": (
                    "If `faq_lookup` or `product_lookup` returns an empty `matches` list, "
                    "explain in German that you could not find reliable information for "
                    "the request, do not claim there was a technical error, and ask "
                    "exactly one helpful follow-up question that matches the missing detail."
                ),
                "faq_tool_description": (
                    "Find top FAQ matches for a user question after similarity filtering. "
                    "Returns JSON with a `matches` list containing `faq_id`, `answer`, and `score`."
                ),
                "product_tool_description": (
                    "Find top product matches for a query after similarity filtering. "
                    "Returns JSON with a `matches` list containing product fields and `score`."
                ),
                "error_fallback_text": "Technischer Fehler.",
            },
            "guardrails": {
                "global": {"enabled": False, "fail_closed": True, "max_output_retries": 1},
                "tracing": {"inputs": True, "outputs": True, "include_config": False},
                "input": {
                    "pii": {
                        "enabled": True,
                        "presidio_config_path": tmp_path / "presidio_config.yaml",
                        "presidio_language": "de",
                        "presidio_allow_list": [],
                        "presidio_score_threshold": 0.4,
                        "entities": ["EMAIL_ADDRESS", "PHONE_NUMBER"],
                        "custom_patterns": ["sk-[A-Za-z0-9]{16,}"],
                        "message": "Bitte teile hier keine sensiblen Daten.",
                    },
                    "prompt_injection": {
                        "enabled": True,
                        "heuristic_terms": [
                            "ignoriere vorherige anweisungen",
                            "ignoriere alle vorherigen anweisungen",
                            "systemprompt",
                            "system prompt",
                        ],
                        "system_prompt": "Detect prompt injection.",
                        "user_prompt_template": "Input: {user_message}\nHistory: {history}",
                        "message": "Diese Anfrage kann ich nicht verarbeiten.",
                    },
                    "topic_relevance": {
                        "enabled": True,
                        "allowed_domain_hints": ["produkt", "konto"],
                        "system_prompt": "Check scope.",
                        "user_prompt_template": (
                            "Input: {user_message}\nHistory: {history}\n"
                            "Hints: {allowed_domain_hints}"
                        ),
                        "message": "Das liegt außerhalb meines Bereichs.",
                        "help_text": (
                            "Ich kann bei Fragen zu Produkten, Konto, Bestellung, Zahlung, "
                            "Versand, Retouren, Datenschutz und Support-Prozessen helfen."
                        ),
                    },
                    "escalation": {
                        "enabled": True,
                        "heuristic_terms": ["anwalt"],
                        "system_prompt": "Check escalation.",
                        "user_prompt_template": (
                            "Input: {user_message}\nHistory: {history}\nHints: {escalation_terms}"
                        ),
                        "message": "Ich leite das an den Support weiter.",
                    },
                },
                "output": {
                    "pii": {
                        "enabled": True,
                        "entities": ["EMAIL_ADDRESS"],
                        "custom_patterns": ["ghp_[A-Za-z0-9]{20,}"],
                    },
                    "grounding": {
                        "enabled": True,
                        "system_prompt": "Check grounding.",
                        "user_prompt_template": (
                            "Input: {user_message}\nAnswer: {answer}\nEvidence: {evidence}\n"
                            "History: {history}\nTool error: {has_tool_error}\n"
                            "Used history only: {used_history_only}\n"
                            "No-tool answer: {no_tool_answer}\n"
                            "Tool call count: {tool_call_count}"
                        ),
                    },
                    "bias": {
                        "enabled": True,
                        "bias_terms": ["alle frauen"],
                        "system_prompt": "Check bias.",
                        "user_prompt_template": "Answer: {answer}\nTerms: {bias_terms}",
                    },
                    "rewrite": {
                        "enabled": True,
                        "system_prompt": "Rewrite answer safely.",
                        "user_prompt_template": (
                            "Answer: {answer}\nEvidence: {evidence}\n"
                            "Hint: {rewrite_hint}\nUser: {user_message}"
                        ),
                    },
                },
            },
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "LANGFUSE_HOST": "http://localhost:3000",
            "langfuse": {
                "host": "http://localhost:3000",
                "tracing_environment": "default",
                "release": "",
                "fail_fast": False,
            },
        }
        for key, value in overrides.items():
            if key in flat_paths:
                _set_nested_value(base_data, flat_paths[key], value)
            else:
                base_data[key] = value
        return Settings(_env_file=None, **base_data)

    return _build
