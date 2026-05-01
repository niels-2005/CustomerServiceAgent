from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from customer_bot.config import Settings
from customer_bot.model_factory import create_guardrail_llm
from tests.e2e._benchmark_helpers import compact_json

BENCHMARK_2_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "benchmark_2.yaml"


class JudgeVerdict(BaseModel):
    """Structured response returned by the local LLM-as-a-judge prompts."""

    score: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)


@dataclass(slots=True)
class JudgeEvaluation:
    """Normalized evaluator output stored in Benchmark 2 reports."""

    score: float
    passed: bool
    reasoning: str


class JudgePromptConfig(BaseModel):
    user_prompt_template: str
    case_pass_threshold: float
    pass_rate_threshold: float


class LLMJudgeConfig(BaseModel):
    enabled: bool
    system_prompt: str
    final_answer: JudgePromptConfig
    query_quality: JudgePromptConfig


class DeterministicTrajectoryConfig(BaseModel):
    match_mode: str
    pass_rate_threshold: float


class Benchmark2EvaluatorConfig(BaseModel):
    llm_judge: LLMJudgeConfig
    deterministic: dict[str, DeterministicTrajectoryConfig]


class Benchmark2Evaluators:
    """Own the local Benchmark 2 evaluators and their config-backed prompts."""

    def __init__(self, settings: Settings) -> None:
        client = create_guardrail_llm(settings)
        if client is None:
            raise RuntimeError("Benchmark 2 judge requires an OpenAI guardrail client.")
        self._client = client
        self._config = _load_benchmark_2_config(BENCHMARK_2_CONFIG_PATH)

    @property
    def final_answer_pass_rate_threshold(self) -> float:
        return self._config.llm_judge.final_answer.pass_rate_threshold

    @property
    def query_quality_pass_rate_threshold(self) -> float:
        return self._config.llm_judge.query_quality.pass_rate_threshold

    @property
    def trajectory_pass_rate_threshold(self) -> float:
        return self._config.deterministic["trajectory"].pass_rate_threshold

    def evaluate_final_answer(
        self,
        *,
        user_message: str,
        answer: str,
        required_facts: list[str],
        forbidden_facts: list[str],
    ) -> JudgeEvaluation:
        config = self._config.llm_judge.final_answer
        return self._evaluate_llm_judge(
            user_prompt=config.user_prompt_template.format(
                user_message=user_message,
                answer=answer,
                required_facts=compact_json(required_facts),
                forbidden_facts=compact_json(forbidden_facts),
            ),
            case_pass_threshold=config.case_pass_threshold,
        )

    def evaluate_query_quality(
        self,
        *,
        expected_tool_calls: list[dict[str, str]],
        actual_tool_calls: list[dict[str, str]],
    ) -> JudgeEvaluation:
        config = self._config.llm_judge.query_quality
        return self._evaluate_llm_judge(
            user_prompt=config.user_prompt_template.format(
                expected_tool_calls=compact_json(expected_tool_calls),
                actual_tool_calls=compact_json(actual_tool_calls),
            ),
            case_pass_threshold=config.case_pass_threshold,
        )

    def evaluate_trajectory(
        self,
        *,
        expected_tool_calls: list[dict[str, str]],
        actual_tool_trajectory: list[str],
    ) -> JudgeEvaluation:
        match_mode = self._config.deterministic["trajectory"].match_mode
        expected_trajectory = [tool_call["tool_name"] for tool_call in expected_tool_calls]
        if match_mode != "exact_ordered_sequence":
            raise RuntimeError(f"Unsupported trajectory match mode: {match_mode}")

        passed = actual_tool_trajectory == expected_trajectory
        if passed:
            reasoning = (
                "Deterministic trajectory match succeeded: "
                f"expected={expected_trajectory} actual={actual_tool_trajectory}"
            )
            return JudgeEvaluation(score=1.0, passed=True, reasoning=reasoning)

        reasoning = (
            "Deterministic trajectory match failed: "
            f"expected={expected_trajectory} actual={actual_tool_trajectory}"
        )
        return JudgeEvaluation(score=0.0, passed=False, reasoning=reasoning)

    def _evaluate_llm_judge(
        self,
        *,
        user_prompt: str,
        case_pass_threshold: float,
    ) -> JudgeEvaluation:
        verdict = asyncio.run(
            self._client.complete_structured(
                system_prompt=self._config.llm_judge.system_prompt,
                user_prompt=user_prompt,
                output_model=JudgeVerdict,
            )
        )
        if not isinstance(verdict, JudgeVerdict):
            raise RuntimeError("Benchmark judge returned an unexpected result type.")

        score = round(verdict.score, 4)
        return JudgeEvaluation(
            score=score,
            passed=score >= case_pass_threshold,
            reasoning=verdict.reasoning.strip(),
        )


def _load_benchmark_2_config(path: Path) -> Benchmark2EvaluatorConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Benchmark2EvaluatorConfig.model_validate(payload)
