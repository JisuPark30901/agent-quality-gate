import asyncio
import os
import time

import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.models import GeminiModel
from deepeval.test_case import LLMTestCase

from agent import answer

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
    JUDGE_MODEL, api_key=os.getenv("GOOGLE_API_KEY"), rpm=JUDGE_RPM
)

CASES = [
    # Normal: answerable from docs/.
    ("normal", "How long do I have to get a full refund?"),
    ("normal", "Can I get a refund on a digital download?"),
    ("normal", "How much does express shipping cost?"),
    ("normal", "Do you ship to South Korea?"),
    # Not in the knowledge base: the agent should say it doesn't know.
    ("out_of_kb", "What is your customer support phone number?"),
    ("out_of_kb", "Do you offer a warranty on electronics?"),
    ("out_of_kb", "Can I pay with PayPal?"),
    # Needs two tools the agent doesn't have (lookup, calculator, date, FX).
    ("two_tools", "Check the status of order #48213 and tell me its delivery date."),
    (
        "two_tools",
        (
            "I paid $40 for an item on September 1. If I return it today, "
            "how much do I get back and in what form?"
        ),
    ),
    (
        "two_tools",
        (
            "Convert the express shipping cost to Korean won at today's rate "
            "and tell me the arrival date if I order now."
        ),
    ),
]


# Core cases run in CI (`-m core`) to stay within free-tier daily limits.
CORE = {1, 2, 5}


@pytest.mark.parametrize(
    "question",
    [
        pytest.param(q, id=f"{cat}-{i}", marks=pytest.mark.core if i in CORE else ())
        for i, (cat, q) in enumerate(CASES, 1)
    ],
)
def test_agent(question: str) -> None:
    reply, context = answer(question)
    test_case = LLMTestCase(
        input=question,
        actual_output=reply,
        retrieval_context=context,
    )
    # Sequential calls and no written reasons keep the judge to 5 calls per test.
    metric_kwargs = {"model": judge, "async_mode": False, "include_reason": False}
    assert_test(
        test_case,
        [
            AnswerRelevancyMetric(threshold=0.7, **metric_kwargs),
            FaithfulnessMetric(threshold=0.7, **metric_kwargs),
        ],
    )
