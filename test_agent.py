import asyncio
import os
import time

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    TaskCompletionMetric,
    ToolCorrectnessMetric,
)
from deepeval.models import GeminiModel
from deepeval.test_case import LLMTestCase, ToolCall
from google.genai import types

from agent import answer

# Pin "today" for the get_today tool so results are the same on any day.
os.environ.setdefault("AGENT_TODAY", "2026-10-03")

# The free tier allows 5 requests per minute per model, so the judge uses a
# different model from the agent and spaces out its calls.
JUDGE_MODEL = os.getenv("JUDGE_MODEL") or "gemini-3.5-flash-lite"
JUDGE_RPM = float(os.getenv("JUDGE_RPM", "5"))


class ThrottledGemini(GeminiModel):
    """GeminiModel that waits between calls to stay under a requests-per-minute limit."""

    def __init__(self, *args, rpm: float, **kwargs):
        super().__init__(*args, **kwargs)
        self._interval = 60 / rpm + 1  # +1s margin
        self._last_call = 0.0

    def _wait_time(self) -> float:
        now = time.monotonic()
        wait = max(0.0, self._last_call + self._interval - now)
        self._last_call = now + wait
        return wait

    def generate(self, *args, **kwargs):
        time.sleep(self._wait_time())
        return super().generate(*args, **kwargs)

    async def a_generate(self, *args, **kwargs):
        await asyncio.sleep(self._wait_time())
        return await super().a_generate(*args, **kwargs)


judge = ThrottledGemini(
    JUDGE_MODEL,
    api_key=os.getenv("GOOGLE_API_KEY"),
    rpm=JUDGE_RPM,
    # Passed through to the Gemini client; a dropped connection must not hang the run.
    http_options=types.HttpOptions(timeout=60_000),
)

# (category, question, tools the agent must call)
CASES = [
    # Normal: answerable from docs/.
    ("normal", "How long do I have to get a full refund?", []),
    ("normal", "Can I get a refund on a digital download?", []),
    ("normal", "How much does express shipping cost?", []),
    ("normal", "Do you ship to South Korea?", []),
    # Not in the knowledge base: the agent should say it doesn't know.
    ("out_of_kb", "What is your customer support phone number?", []),
    ("out_of_kb", "Do you offer a warranty on electronics?", []),
    ("out_of_kb", "Can I pay with PayPal?", []),
    # Needs two tools (see tools.py for the mock data).
    (
        "two_tools",
        "Check order #48213 and tell me how many days are left until it arrives.",
        ["lookup_order", "get_today"],
    ),
    (
        "two_tools",
        "If I return order #51007 today, how much money do I get back and in what form?",
        ["lookup_order", "get_today"],
    ),
    (
        "two_tools",
        (
            "Convert the express shipping cost to Korean won and tell me "
            "the arrival date if I order today."
        ),
        ["convert_currency", "get_today"],
    ),
]

# Core cases run in CI (`-m core`): one per category, to stay within
# free-tier daily limits.
CORE = {1, 5, 8}


@pytest.mark.parametrize(
    ("category", "question", "expected_tools"),
    [
        pytest.param(*case, id=f"{case[0]}-{i}", marks=pytest.mark.core if i in CORE else ())
        for i, case in enumerate(CASES, 1)
    ],
)
def test_agent(category: str, question: str, expected_tools: list[str]) -> None:
    result = answer(question)
    test_case = LLMTestCase(
        input=question,
        actual_output=result.text,
        retrieval_context=result.context,
        tools_called=[
            ToolCall(name=u.name, input_parameters=u.args, output=u.output)
            for u in result.tool_uses
        ],
        expected_tools=[ToolCall(name=name) for name in expected_tools],
    )
    # Sequential calls and no written reasons keep judge calls to a minimum.
    metric_kwargs = {"model": judge, "async_mode": False, "include_reason": False}
    if category == "two_tools":
        metrics = [
            # Compares tool names directly; no judge call. 1.0 = every
            # expected tool was called.
            ToolCorrectnessMetric(threshold=1.0, **metric_kwargs),
            TaskCompletionMetric(threshold=0.7, **metric_kwargs),
        ]
    else:
        metrics = [
            AnswerRelevancyMetric(threshold=0.7, **metric_kwargs),
            FaithfulnessMetric(threshold=0.7, **metric_kwargs),
        ]
    assert_test(test_case, metrics)
