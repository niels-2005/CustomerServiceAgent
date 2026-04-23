from __future__ import annotations

from typing import Any

from llama_index.core.agent.workflow.workflow_events import AgentOutput

from customer_bot.retrieval.types import ProductRetrievalResult, RetrievalResult


class FakeRetriever:
    def __init__(self, result: RetrievalResult) -> None:
        self._result = result
        self.queries: list[str] = []

    def retrieve_best_answer(self, query: str) -> RetrievalResult:
        self.queries.append(query)
        return self._result


class FakeProductRetriever:
    def __init__(self, result: ProductRetrievalResult) -> None:
        self._result = result
        self.queries: list[str] = []

    def retrieve_products(self, query: str) -> ProductRetrievalResult:
        self.queries.append(query)
        return self._result


class FakeHandler:
    def __init__(self, events: list[Any], result: AgentOutput) -> None:
        self._events = events
        self._result = result

    async def stream_events(self):
        for event in self._events:
            yield event

    async def _resolve(self) -> AgentOutput:
        return self._result

    def __await__(self):
        return self._resolve().__await__()


class FakeObservation:
    def __init__(self, *, start_kwargs: dict[str, Any] | None = None) -> None:
        self.start_kwargs = start_kwargs or {}
        self.updates: list[dict[str, Any]] = []
        self.children: list[FakeObservation] = []
        self.ended = False

    def update(self, **kwargs: Any) -> None:
        self.updates.append(kwargs)

    def start_observation(self, **kwargs: Any) -> FakeObservation:
        child = FakeObservation(start_kwargs=kwargs)
        self.children.append(child)
        return child

    def end(self) -> None:
        self.ended = True


class FakeObservationContext:
    def __init__(self, observation: FakeObservation) -> None:
        self._observation = observation

    def __enter__(self) -> FakeObservation:
        return self._observation

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeLangfuseClient:
    def __init__(self, observation: FakeObservation) -> None:
        self.observation = observation
        self.calls: list[dict[str, Any]] = []

    def start_as_current_observation(self, **kwargs: Any) -> FakeObservationContext:
        self.calls.append(kwargs)
        return FakeObservationContext(self.observation)


class FakeSessionContext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False
