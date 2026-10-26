"""
tracing.py - Arize AX tracing setup for the OpenAI Agents SDK.

IMPORT ORDER IS CRITICAL: this file must be imported before agent.py (and
before the `agents` package is imported anywhere). OpenInference works by
patching the agents SDK at import time, so if the SDK loads first, the
instrumentation misses the early setup calls and spans are incomplete.

The pattern here follows the Arize docs exactly:
  1. register() creates an OTel TracerProvider pointing at Arize
  2. OpenAIAgentsInstrumentor().instrument(...) patches the SDK so every
     agent run, tool call, and model call automatically emits a span
"""

import os
from dotenv import load_dotenv
from arize.otel import register
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor

# Load .env before reading any env vars
load_dotenv()

# ---------------------------------------------------------------------------
# Register the Arize OTel exporter
# ---------------------------------------------------------------------------
# register() creates a TracerProvider that ships spans to Arize via OTLP/gRPC.
#
# Endpoint defaults to US (https://otlp.arize.com/v1).
# If you are on EU or Canada, add ARIZE_COLLECTOR_ENDPOINT to your .env:
#   EU:     https://otlp.eu-west-1a.arize.com/v1
#   Canada: https://otlp.ca-central-1a.arize.com/v1
#
# ARIZE_SPACE_ID must be the base64 Space ID (not the human-readable name).
# Find it at app.arize.com -> Settings -> Spaces.
tracer_provider = register(
    space_id=os.environ["ARIZE_SPACE_ID"],
    api_key=os.environ["ARIZE_API_KEY"],
    project_name="account-health-agent",  # groups all runs in the Arize UI
)

# ---------------------------------------------------------------------------
# Instrument the OpenAI Agents SDK
# ---------------------------------------------------------------------------
# This single call patches the SDK so that every:
#   - Runner.run()       → emits an "agent" root span
#   - tool invocation    → emits a child "tool" span
#   - model API call     → emits a child "llm" span
#
# You do NOT need to add any tracing code in agent.py, tools.py, or run.py.
# The instrumentation is transparent — it just works once this file is imported.
OpenAIAgentsInstrumentor().instrument(tracer_provider=tracer_provider)

print("Arize AX tracing initialized → project: account-health-agent")
