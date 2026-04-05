from __future__ import annotations

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.llms.llm import LLM
from llama_index.core.tools import FunctionTool
from opentelemetry import trace

from customer_bot.config import Settings
from customer_bot.llama import create_llm
from customer_bot.retrieval.service import FaqRetrieverService

FAQ_TOOL_NAME = "faq_lookup"


class AgentService:
    def __init__(
        self,
        settings: Settings,
        retriever: FaqRetrieverService,
        llm: LLM | None = None,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._llm = llm or create_llm(settings)
        self._tracer = trace.get_tracer("customer_bot.agent")

    async def answer(
        self,
        user_message: str,
        chat_history: list[ChatMessage],
        session_id: str,
    ) -> str:
        tool = self._build_tool(session_id=session_id)
        agent = FunctionAgent(
            name="FAQAgent",
            description="Agent for FAQ-only customer support responses",
            system_prompt=(
                "You are a customer support FAQ assistant. "
                "Always call the faq_lookup tool with the user question and "
                "return the tool output exactly as-is."
            ),
            tools=[tool],
            llm=self._llm,
            streaming=False,
        )

        handler = agent.run(user_msg=user_message, chat_history=chat_history)
        result = await handler

        content = (result.response.content or "").strip()
        if not content:
            return self._settings.fallback_text
        return content

    def _build_tool(self, session_id: str) -> FunctionTool:
        def faq_lookup(question: str) -> str:
            with self._tracer.start_as_current_span("faq_retrieval") as span:
                span.set_attribute("session.id", session_id)
                span.set_attribute("tool.name", FAQ_TOOL_NAME)
                span.set_attribute("retrieval.query", question)

                retrieval_result = self._retriever.retrieve_best_answer(question)
                has_match = retrieval_result.answer is not None
                span.set_attribute("retrieval.match", has_match)
                if retrieval_result.score is not None:
                    span.set_attribute("retrieval.score", retrieval_result.score)

                if not has_match:
                    return self._settings.fallback_text

                return retrieval_result.answer or self._settings.fallback_text

        return FunctionTool.from_defaults(
            fn=faq_lookup,
            name=FAQ_TOOL_NAME,
            description=(
                "Find the best matching FAQ answer for a user question. "
                "Returns a plain German answer string."
            ),
            return_direct=True,
        )
