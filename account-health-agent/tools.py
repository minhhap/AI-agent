"""
tools.py - The three data-fetching tools the agent can call.

Each function is decorated with @function_tool, which tells the OpenAI Agents
SDK to expose it as a callable tool. The SDK reads the docstring and type
annotations to build the JSON schema it sends to the model - so clear
docstrings ARE the tool descriptions the model uses to decide when to call them.
"""

import csv
from pathlib import Path
from agents import function_tool

# Resolve the data directory relative to this file so the project works
# regardless of where you run it from.
DATA_DIR = Path(__file__).parent / "data"


def _match_name(stored: str, query: str) -> bool:
    """
    Return True if query matches stored account name.
    Tries exact match first (case-insensitive), then substring match.
    This lets "Acme" match "Acme Corp" when the model extracts a short name.
    """
    stored_l = stored.lower()
    query_l = query.lower()
    return stored_l == query_l or query_l in stored_l


@function_tool
def get_account(account_name: str) -> str:
    """
    Look up an account's profile: plan tier, Annual Recurring Revenue (ARR),
    and contract renewal date. Call this first to establish basic account context.
    Returns a plain-text summary, or an error message if the account is not found.
    """
    with open(DATA_DIR / "accounts.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if _match_name(row["name"], account_name):
                return (
                    f"Account: {row['name']}\n"
                    f"Plan: {row['plan']}\n"
                    f"ARR: ${int(row['arr']):,}\n"
                    f"Renewal date: {row['renewal_date']}"
                )

    return f"Account '{account_name}' not found. Check the spelling or try a different name."


@function_tool
def get_usage(account_name: str) -> str:
    """
    Retrieve the last 6 months of Monthly Active Users (MAU) for an account.
    Use this to identify usage trends: is the account growing, stable, or declining?
    A significant decline (e.g. >20%) is a churn risk signal.
    Returns a month-by-month breakdown and the percentage change from first to last month.
    """
    rows = []
    with open(DATA_DIR / "usage.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if _match_name(row["account"], account_name):
                rows.append(row)

    if not rows:
        return f"No usage data found for '{account_name}'."

    # Sort chronologically so the trend reads oldest -> newest
    rows.sort(key=lambda r: r["month"])

    lines = ["Monthly Active Users (last 6 months):"]
    for row in rows:
        lines.append(f"  {row['month']}: {row['monthly_active_users']} MAU")

    # Calculate the overall trend percentage
    first = int(rows[0]["monthly_active_users"])
    last = int(rows[-1]["monthly_active_users"])
    change_pct = ((last - first) / first) * 100
    direction = "increase" if change_pct >= 0 else "decline"
    lines.append(f"\nTrend: {abs(change_pct):.1f}% {direction} over the period.")

    return "\n".join(lines)


@function_tool
def get_tickets(account_name: str) -> str:
    """
    Fetch all support tickets filed by an account, including date, severity
    (low / medium / high), and a summary of the issue.
    Use this to spot patterns: repeated high-severity tickets, recent escalations,
    or unresolved issues signal dissatisfaction. Feature requests or upsell
    inquiries signal expansion potential.
    Returns tickets sorted newest-first, or a message if there are none on record.
    """
    rows = []
    with open(DATA_DIR / "tickets.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if _match_name(row["account"], account_name):
                rows.append(row)

    if not rows:
        return f"No support tickets found for '{account_name}'."

    # Sort newest-first so the most recent issues appear at the top
    rows.sort(key=lambda r: r["date"], reverse=True)

    lines = [f"Support tickets ({len(rows)} total, newest first):"]
    for row in rows:
        lines.append(f"  [{row['date']}] [{row['severity'].upper()}] {row['summary']}")

    return "\n".join(lines)
