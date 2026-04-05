from __future__ import annotations

import pytest

from customer_bot.observability import initialize_observability


@pytest.mark.unit
def test_observability_fails_fast_without_keys(settings_factory) -> None:
    settings = settings_factory(
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
        langfuse_fail_fast=True,
    )

    with pytest.raises(RuntimeError, match="Langfuse keys are missing"):
        initialize_observability(settings)


@pytest.mark.unit
def test_observability_non_fatal_without_keys(settings_factory) -> None:
    settings = settings_factory(
        LANGFUSE_PUBLIC_KEY="",
        LANGFUSE_SECRET_KEY="",
        langfuse_fail_fast=False,
    )

    client = initialize_observability(settings)

    assert client is None
