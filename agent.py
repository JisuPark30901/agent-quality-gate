"""Q&A agent that answers from the documents in docs/ and can call tools."""

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import TOOLS

load_dotenv()

DOCS_DIR = Path(__file__).parent / "docs"
MODEL = os.getenv("GEMINI_MODEL") or "gemini-3.7-flash"
TOP_K = 2

SYSTEM_PROMPT = (
    "Answer the question using only the provided context and the results of "
    "your tools. Use the tools for order lookups, today's date, and currency "
    "conversion. If neither the context nor the tools contain the answer, "
    "say you don't know."
)


@dataclass
class ToolUse:
    name: str
    args: dict
    output: object


@dataclass
class AgentResult:
    text: str
    context: list[str]
    tool_uses: list[ToolUse] = field(default_factory=list)


def load_docs(docs_dir: Path = DOCS_DIR) -> list[str]:
    return [p.read_text() for p in sorted(docs_dir.glob("*.md"))]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve(question: str, docs: list[str], k: int = TOP_K) -> list[str]:
    """Return the k docs that share the most words with the question."""
    query = _words(question)
    ranked = sorted(docs, key=lambda d: len(query & _words(d)), reverse=True)
    return ranked[:k]


def _tool_uses(history: list[types.Content]) -> list[ToolUse]:
    """Pair each function call in the chat history with its response."""
    calls, outputs = [], {}
    for content in history:
        for part in content.parts or []:
            if part.function_call:
                calls.append(part.function_call)
            if part.function_response:
                outputs.setdefault(part.function_response.name, []).append(
                    part.function_response.response
                )
    return [
        ToolUse(c.name, dict(c.args or {}), (outputs.get(c.name) or [None]).pop(0))
        for c in calls
    ]


def answer(question: str, client: genai.Client | None = None) -> AgentResult:
    """Answer a question, calling tools as needed."""
    # Reads GOOGLE_API_KEY; retries 429/5xx since Gemini often returns 503 under load.
    client = client or genai.Client(
        http_options=types.HttpOptions(
            timeout=60_000,  # ms; a dropped connection must not hang the run
            retry_options=types.HttpRetryOptions(attempts=5, initial_delay=2),
        ),
    )
    context = retrieve(question, load_docs())
    # The SDK runs the Python tools automatically and records the calls.
    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            tools=TOOLS,
        ),
    )
    response = chat.send_message(
        "Context:\n\n" + "\n\n".join(context) + f"\n\nQuestion: {question}"
    )
    history = chat.get_history(curated=False)
    return AgentResult(response.text, context, _tool_uses(history))


def main() -> None:
    question = " ".join(sys.argv[1:]) or "How long do I have to get a refund?"
    result = answer(question)
    for use in result.tool_uses:
        print(f"[tool] {use.name}({use.args}) -> {use.output}")
    print(f"Q: {question}\nA: {result.text}")


if __name__ == "__main__":
    main()
