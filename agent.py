"""Q&A agent that answers questions using only the documents in docs/."""

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

DOCS_DIR = Path(__file__).parent / "docs"
MODEL = os.getenv("GEMINI_MODEL") or "gemini-3.7-flash"
TOP_K = 2

SYSTEM_PROMPT = (
    "Answer the question using only the provided context. "
    "If the context does not contain the answer, say you don't know."
)


def load_docs(docs_dir: Path = DOCS_DIR) -> list[str]:
    return [p.read_text() for p in sorted(docs_dir.glob("*.md"))]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve(question: str, docs: list[str], k: int = TOP_K) -> list[str]:
    """Return the k docs that share the most words with the question."""
    query = _words(question)
    ranked = sorted(docs, key=lambda d: len(query & _words(d)), reverse=True)
    return ranked[:k]


def answer(question: str, client: genai.Client | None = None) -> tuple[str, list[str]]:
    """Answer a question and return the answer with the context it used."""
    # Reads GOOGLE_API_KEY; retries 429/5xx since Gemini often returns 503 under load.
    client = client or genai.Client(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=5, initial_delay=2),
        ),
    )
    context = retrieve(question, load_docs())
    response = client.models.generate_content(
        model=MODEL,
        contents="Context:\n\n" + "\n\n".join(context) + f"\n\nQuestion: {question}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True,
            ),
        ),
    )
    return response.text, context


def main() -> None:
    question = " ".join(sys.argv[1:]) or "How long do I have to get a refund?"
    reply, _ = answer(question)
    print(f"Q: {question}\nA: {reply}")


if __name__ == "__main__":
    main()
