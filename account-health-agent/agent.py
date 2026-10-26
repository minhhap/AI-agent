"""
agent.py - Creates and exports the account health agent.

Responsibilities:
  1. Load secrets from .env
  2. Point the SDK at OpenRouter instead of OpenAI directly
  3. Define the agent: its instructions, its tools, and its model
"""

import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, set_default_openai_client, set_default_openai_api
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from tools import get_account, get_usage, get_tickets

# ---------------------------------------------------------------------------
# 1. Load secrets
# ---------------------------------------------------------------------------
# load_dotenv() reads .env and injects each line as an environment variable.
# It does nothing if a variable is already set, so real env vars always win.
load_dotenv()

# ---------------------------------------------------------------------------
# 2. Configure OpenRouter as the model provider
# ---------------------------------------------------------------------------
# The OpenAI Agents SDK is designed around the OpenAI API, but OpenRouter
# exposes an OpenAI-compatible endpoint. We just swap the base_url.
#
# use_for_tracing=False is CRITICAL here: it tells the SDK not to use this
# client to send traces to OpenAI. We want traces going to Arize instead.
# If we left this as True, the SDK would try (and fail) to ship trace data
# to OpenRouter, and it would conflict with Arize instrumentation.
openrouter_client = AsyncOpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)
set_default_openai_client(openrouter_client, use_for_tracing=False)

# Tell the SDK to use the Chat Completions API (not the Responses API).
# OpenRouter only supports Chat Completions, and this also matches what
# Arize's OpenInference instrumentor hooks into.
set_default_openai_api("chat_completions")

# ---------------------------------------------------------------------------
# 3. Define the agent
# ---------------------------------------------------------------------------
# The MODEL env var lets you swap models in .env without touching code.
# E.g. switch to "anthropic/claude-3.5-sonnet" for a stronger model.
MODEL = os.environ.get("MODEL", "openai/gpt-4.1-mini")

account_health_agent = Agent(
    name="Account Health Agent",

    # The system prompt. This is the most important thing you write.
    # It tells the model its role, what output format to produce,
    # and how to reason about the data it gets back from tools.
    instructions="""
You are an account health assistant for a Customer Success Manager.

When asked about an account, always call all three tools in order:
  1. get_account   - to get the plan, ARR, and renewal date
  2. get_usage     - to get the 6-month usage trend
  3. get_tickets   - to get support ticket history

Then produce a structured report in this exact format:

RISK LEVEL: <Low | Medium | High>

EVIDENCE:
- <key finding from account data>
- <key finding from usage trend>
- <key finding from tickets>

NEXT STEPS:
1. <specific, actionable recommendation>
2. <specific, actionable recommendation>

Base the risk level on this rubric:
- High:   significant usage decline (>20%) AND/OR multiple high-severity tickets
          AND/OR renewal within 60 days with unresolved issues
- Medium: moderate usage decline OR unresolved medium-severity tickets
          OR renewal within 90 days with mixed signals
- Low:    stable or growing usage, no high-severity tickets, renewal not imminent

Keep the tone professional and concise. Cite specific numbers and dates.
""",

    # The three tools. The agent loop will call these as needed.
    tools=[get_account, get_usage, get_tickets],

    # Bypass the SDK's provider-prefix router (which only knows openai/anthropic/etc.)
    # by passing an explicit model object tied to our OpenRouter client.
    # This means ANY OpenRouter model string works: openai/..., google/..., etc.
    model=OpenAIChatCompletionsModel(model=MODEL, openai_client=openrouter_client),
)
