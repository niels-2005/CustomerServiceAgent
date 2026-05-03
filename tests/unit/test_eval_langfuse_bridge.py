from __future__ import annotations

from tests.evals.langfuse_bridge import _extract_tool_call_payload


class _Observation:
    def __init__(
        self,
        *,
        type: str,
        name: str,
        input: object,
        output: object,
        metadata: object | None = None,
        level: str | None = None,
    ) -> None:
        self.type = type
        self.name = name
        self.input = input
        self.output = output
        self.metadata = metadata
        self.level = level


def test_extract_tool_call_payload_accepts_uppercase_tool_type() -> None:
    observation = _Observation(
        type="TOOL",
        name="faq_lookup",
        input={"question": "Wie setze ich mein Passwort zurück?"},
        output={
            "matches": [
                {
                    "faq_id": "faq_7",
                    "answer": "Passwort vergessen.",
                    "score": 0.91,
                }
            ]
        },
    )

    payload = _extract_tool_call_payload(observation)

    assert payload == {
        "tool_name": "faq_lookup",
        "tool_input": {"question": "Wie setze ich mein Passwort zurück?"},
        "tool_output": {
            "matches": [
                {
                    "faq_id": "faq_7",
                    "answer": "Passwort vergessen.",
                    "score": 0.91,
                }
            ]
        },
        "is_error": False,
    }


def test_extract_tool_call_payload_uses_metadata_tool_name_and_raw_output() -> None:
    observation = _Observation(
        type="TOOL",
        name="FunctionTool.acall",
        input={"kwargs": {"question": "Wie setze ich mein Passwort zurück?"}},
        output={
            "raw_output": (
                '{"matches":[{"faq_id":"faq_7","answer":"Passwort vergessen.","score":0.91}]}'
            )
        },
        metadata={"attributes": {"tool.name": "faq_lookup"}},
        level="ERROR",
    )

    payload = _extract_tool_call_payload(observation)

    assert payload == {
        "tool_name": "faq_lookup",
        "tool_input": {"question": "Wie setze ich mein Passwort zurück?"},
        "tool_output": {
            "matches": [
                {
                    "faq_id": "faq_7",
                    "answer": "Passwort vergessen.",
                    "score": 0.91,
                }
            ]
        },
        "is_error": True,
    }
