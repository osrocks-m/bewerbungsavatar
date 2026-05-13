#!/usr/bin/env python3
"""
CLI to chat with the LangGraph graph directly — no server or database needed.
Run from the ai-app/ directory with the venv active:

    source .venv/bin/activate
    python chat.py
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

# The .env lives at the project root, one level above ai-app/.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.llm import stream_graph


async def main() -> None:
    history: list[BaseMessage] = []
    bewerbung_id = input("Bewerbung ID: ").strip()
    print("Chat started — Ctrl+C or type 'quit' to exit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        print("AI: ", end="", flush=True)
        full_response = ""

        async for token in stream_graph(question, history, bewerbung_id):
            print(token, end="", flush=True)
            full_response += token

        print()

        history.append(HumanMessage(content=question))
        history.append(AIMessage(content=full_response))


if __name__ == "__main__":
    asyncio.run(main())
