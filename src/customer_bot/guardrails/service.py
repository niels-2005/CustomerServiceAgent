from __future__ import annotations

from llama_index.core.base.llms.types import ChatMessage

from customer_bot.agent.service import AgentAnswerResult
from customer_bot.config import Settings
from customer_bot.guardrails.input import InputGuardPipeline
from customer_bot.guardrails.llm import LlmGuardExecutor
from customer_bot.guardrails.models import (
    GuardrailInputResult,
    GuardrailOutputResult,
    GuardrailRewriteResult,
)
from customer_bot.guardrails.output import OutputGuardPipeline
from customer_bot.guardrails.rewrite import RewriteService
from customer_bot.guardrails.tracing import GuardrailTraceHelper
from customer_bot.guardrails.validators import (
    BiasGuard,
    EscalationGuard,
    GroundingGuard,
    OutputSensitiveDataGuard,
    PromptInjectionGuard,
    SecretPIIGuard,
    TopicRelevanceGuard,
)
from customer_bot.model_factory import GuardrailOpenAIClient


class GuardrailService:
    def __init__(self, settings: Settings, llm_client: GuardrailOpenAIClient | None) -> None:
        trace_helper = GuardrailTraceHelper(settings)
        executor = LlmGuardExecutor(llm_client, trace_helper)
        self._settings = settings
        self._trace_helper = trace_helper
        self._input_pipeline = InputGuardPipeline(
            settings=settings,
            trace_helper=trace_helper,
            pii_guard=SecretPIIGuard(settings),
            prompt_injection_guard=PromptInjectionGuard(settings, executor),
            topic_relevance_guard=TopicRelevanceGuard(settings, executor),
            escalation_guard=EscalationGuard(settings, executor),
        )
        self._output_pipeline = OutputGuardPipeline(
            settings=settings,
            trace_helper=trace_helper,
            output_pii_guard=OutputSensitiveDataGuard(settings),
            grounding_guard=GroundingGuard(settings, executor),
            bias_guard=BiasGuard(settings, executor),
        )
        self._rewrite_service = RewriteService(settings, executor, trace_helper)

    async def evaluate_input(
        self,
        *,
        user_message: str,
        chat_history: list[ChatMessage],
        parent_observation=None,
    ) -> GuardrailInputResult:
        with self._trace_helper.start_stage(
            parent_observation,
            name="input_guardrails",
            input_value={"user_message": user_message},
            metadata={"phase": "input"},
        ) as stage:
            result = await self._input_pipeline.run(
                user_message=user_message,
                chat_history=chat_history,
                parent_observation=stage,
            )
            self._trace_helper.update_observation(
                stage,
                output={"action": result.action, "sanitized": result.sanitized},
                metadata={"phase": "input", "action": result.action, "reason": result.reason},
                level="WARNING" if result.action != "allow" else None,
            )
            return result

    async def evaluate_output(
        self,
        *,
        user_message: str,
        answer: str,
        chat_history: list[ChatMessage],
        agent_result: AgentAnswerResult,
        parent_observation=None,
    ) -> GuardrailOutputResult:
        compact_history = self._compact_history(chat_history)
        with self._trace_helper.start_stage(
            parent_observation,
            name="output_guardrails",
            input_value={"answer": answer},
            metadata={"phase": "output"},
        ) as stage:
            result = await self._output_pipeline.run(
                user_message=user_message,
                answer=answer,
                compact_history=compact_history,
                agent_result=agent_result,
                parent_observation=stage,
            )
            self._trace_helper.update_observation(
                stage,
                output={
                    "action": result.action,
                    "rewrite_hint": result.rewrite_hint,
                    "sanitized": result.sanitized,
                },
                metadata={"phase": "output", "action": result.action, "reason": result.reason},
                level="WARNING" if result.action != "allow" else None,
            )
            return result

    async def rewrite_output(
        self,
        *,
        answer: str,
        rewrite_hint: str,
        user_message: str,
        agent_result: AgentAnswerResult,
        parent_observation=None,
    ) -> GuardrailRewriteResult:
        with self._trace_helper.start_stage(
            parent_observation,
            name="output_rewrite",
            input_value={
                "answer": answer,
                "rewrite_hint": rewrite_hint,
                "evidence": agent_result.evidence,
            },
            metadata={"phase": "rewrite"},
        ) as stage:
            result = await self._rewrite_service.rewrite(
                answer=answer,
                rewrite_hint=rewrite_hint,
                evidence=agent_result.evidence,
                user_message=user_message,
                parent_observation=stage,
            )
            self._trace_helper.update_observation(
                stage,
                output={"answer": result.answer, "sanitized": result.sanitized},
                metadata={"phase": "rewrite"},
            )
            return result

    @staticmethod
    def _compact_history(chat_history: list[ChatMessage]) -> str:
        snippets = []
        for message in chat_history[-4:]:
            content = (message.content or "").strip()
            if content:
                snippets.append(f"{message.role}: {content}")
        return "\n".join(snippets)
