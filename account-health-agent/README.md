# Account Health Agent

An LLM-powered assistant for Customer Success Managers. Ask a natural-language question like _"How is Acme doing?"_ and the agent checks the account's profile, usage trend, and support tickets, then returns a structured risk assessment with evidence and next steps.

---

## What it does

```
$ python run.py "How is Acme doing?"

RISK LEVEL: High

EVIDENCE:
- Enterprise plan, $120,000 ARR, renewal on 2026-12-01 (37 days away)
- MAU dropped 40.4% over 6 months (520 → 310)
- 4 high-severity tickets since August, including a CTO escalation
  threatening cancellation (2026-10-18)

NEXT STEPS:
1. Schedule an executive alignment call this week with Engineering leadership
2. Escalate SSO and dashboard issues with a formal RCA within 48 hours
```

---

## Architecture

```
run.py
  │
  ├─ tracing.py          ← Arize AX instrumentation (must import first)
  │
  └─ agent.py            ← OpenRouter client + Agent definition
       │
       └─ tools.py       ← Three @function_tool functions that read CSVs
            │
            └─ data/
                 ├─ accounts.csv   (plan, ARR, renewal date)
                 ├─ usage.csv      (6 months of MAU per account)
                 └─ tickets.csv    (support ticket history)
```

The agent loop runs inside the OpenAI Agents SDK's `Runner.run()`:

1. The model receives the user question, the system prompt, and the JSON schemas of all three tools.
2. It decides to call `get_account` → the SDK runs the function → the result is added to the conversation.
3. It calls `get_usage`, then `get_tickets`, the same way.
4. Once all three tools have returned, the model produces a final text response with no more tool calls.
5. The SDK returns that response as `result.final_output`.

No routing logic is written by hand. The model decides the call sequence based on the tool descriptions in the docstrings.

---

## Stack and why

| Choice | Reason |
|---|---|
| **OpenAI Agents SDK** | Minimal surface area: `Agent`, `Runner`, `@function_tool`. The loop, tool dispatch, and result handling are all built in. No graph DSL, no config files. Easy to read in an interview. |
| **OpenRouter** | One API key, hundreds of models (OpenAI, Anthropic, Google, Meta). Swap `MODEL` in `.env` with no code changes. Useful when evaluating models or managing cost. |
| **Arize AX** | Captures every agent run, tool call, and model call as a structured trace. Essential for debugging non-deterministic agent behavior and for evaluating output quality at scale. |
| **`@function_tool`** | The decorator turns a plain Python function into a tool the model can call. The docstring becomes the tool description the model sees — clear docstrings matter more than the code. |

---

## How tools work

The `@function_tool` decorator does two things:

1. **Reads the type annotations** to build the JSON schema for the tool's parameters. `account_name: str` becomes `{"type": "string", "name": "account_name"}` in the schema sent to the model.

2. **Reads the docstring** to build the tool's description. The model uses this description — not the function body — to decide whether and when to call a tool.

This means writing a tool is really writing documentation for the model. A vague docstring produces unreliable tool selection. A docstring like _"A significant decline (>20%) is a churn risk signal"_ directly shapes the model's reasoning.

All three tools return plain strings. The SDK feeds those strings back to the model as tool result messages, and the model incorporates them into its next response.

---

## Setup

```bash
git clone <this-repo>
cd account-health-agent

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.template .env
# Edit .env: fill in OPENROUTER_API_KEY, ARIZE_SPACE_ID, ARIZE_API_KEY, MODEL

python run.py "How is Acme doing?"
```

---

## Moving to production

This demo reads from CSV files. Here is how each piece would be replaced in a real deployment.

**Replace CSVs with live data sources**

| Current | Production replacement |
|---|---|
| `data/accounts.csv` | Salesforce / HubSpot CRM API, or a `salesforce` MCP server |
| `data/usage.csv` | Data warehouse query (Snowflake, BigQuery) via an analytics API |
| `data/tickets.csv` | Zendesk or Jira API |

The tool functions are the only thing that changes — `get_account` switches from `csv.DictReader` to an API call. The agent, the instructions, and the output format stay identical.

**MCP as a drop-in for tools**

The OpenAI Agents SDK supports MCP (Model Context Protocol) servers natively. A Salesforce MCP server exposes `get_account`, `get_usage`, and similar operations as MCP tools. The agent calls them the same way it calls `@function_tool` functions — no code change on the agent side.

**Productionizing the runner**

- Wrap `Runner.run()` in a FastAPI endpoint so any internal tool can call it over HTTP.
- Add a Slack bolt handler so CSMs can ask `@health-bot How is Acme doing?` in Slack.
- Cache tool results with a short TTL (e.g. 5 minutes) to avoid hammering the CRM on repeated questions.
- Add input validation: confirm the account exists before starting the agent loop, and return a 404-style message early rather than letting the model handle it.

**Observability at scale**

With Arize AX already wired in, you get traces for free in production. The next step is adding Arize evaluators — automated LLM judges that score each response for accuracy, groundedness, and format compliance. This turns the trace log into a quality dashboard you can alert on.
