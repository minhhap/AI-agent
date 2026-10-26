"""
run.py - Command-line entry point.

Usage:
    python run.py "How is Acme doing?"
    python run.py "Give me a health check on Globex"
    python run.py "What's the status of Initech?"
"""

import sys
import asyncio

# tracing MUST be imported first — before `agents` or `agent` are imported.
# OpenInference patches the SDK at import time; a late import misses spans.
import tracing  # noqa: F401  (imported for side effects only)

from agents import Runner
from agent import account_health_agent


async def run_query(question: str) -> str:
    """Run the agent on a single question and return the final text output."""
    result = await Runner.run(account_health_agent, question)
    return result.final_output


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py \"How is Acme doing?\"")
        sys.exit(1)

    # Join all args so you don't need quotes: python run.py How is Acme doing?
    question = " ".join(sys.argv[1:])

    print(f"\nQuestion: {question}")
    print("-" * 60)

    answer = asyncio.run(run_query(question))
    print(answer)


if __name__ == "__main__":
    main()
