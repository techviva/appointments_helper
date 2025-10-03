from typing import Any, Dict
import datetime as dt

def _tool_schema(name: str, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    return {"name": name, "description": description, "parameters": parameters}

TOOLS = [
    _tool_schema(
        "parse_slack_message_to_request",
        "Parse Slack text into a structured new-appointment request.",
        {"type": "object", "properties": {"slack_text": {"type": "string"}}, "required": ["slack_text"]},
    ),
    _tool_schema(
        "get_calendar_appointments",
        "Fetch existing appointments for a Google Calendar ID in an interval.",
        {"type": "object", "properties": {
            "consultant_calendar_id": {"type": "string"},
            "time_min_iso": {"type": "string"},
            "time_max_iso": {"type": "string"},
        }, "required": ["consultant_calendar_id", "time_min_iso"]},
    ),
    _tool_schema(
        "get_clickup_availability",
        "Fetch availability windows for a customer within a date range.",
        {"type": "object", "properties": {
            "customer_id": {"type": "string"},
            "date_from": {"type": "string"},
            "date_to": {"type": "string"},
        }, "required": ["customer_id", "date_from", "date_to"]},
    ),
    _tool_schema(
        "optimize_routes",
        "Call Google Route Optimization to propose schedules (uses your optimize_visits).",
        {"type": "object", "properties": {
            "addresses": {"type": "array", "items": {"type": "object"}},
            "vehicle_start_point": {"type": "array", "items": {"type": "number"}},
            "vehicle_end_point": {"type": "array", "items": {"type": "number"}},
            "global_start_time": {"type": "string"},
            "global_end_time": {"type": "string"},
        }, "required": ["addresses"]},
    ),
]

today_date = dt.datetime.now().date().isoformat()

SYSTEM_PROMPT = """
You are the Route Optimization Orchestrator Agent.

Hard constraints you must honor:
1) Do NOT move an appointment to a day when that customer is not available.
2) You MAY move an appointment only within availability windows for that customer.
3) Keep default service duration at 60 minutes unless specified.
4) Respect ISO8601 timezones (-07:00 for Phoenix) in all reasoning.

Plan:
- Parse the Slack text for new request, availability, and address.
- Get existing appointments from Clickup.
- For each customer involved (existing + new), obtain availability windows (Slack and/or ClickUp).
- Build time windows per stop and call the route optimization tool.
- Return best 1–2 options with a concise explanation and a JSON payload of the chosen plan.
"""


PARSE_NOTE_PROMPT = """
You are an AI scheduling assistant.  
Your task is to parse natural-language customer availability text and output a normalized JSON object with `time_windows`.  

### Rules
1. Today's date is {}. Use this as reference when interpreting relative dates.
2. If availability is vague or missing, assume: Monday-Friday 9am-5pm for the next 7 days.
3. If customer says "flexible" or "anytime" without specifics, return weekday business hours.
4. Use 24-hour ISO 8601 timestamps with timezone offset (Phoenix: `-07:00`).
5. Always return at least ONE time window, even if you have to infer it.
6. Output format: {{"time_windows": [{{"start": "ISO_DATE", "end": "ISO_DATE"}}]}}

### Examples of vague input and how to handle:
- "Call me back" → weekday mornings 9am-12pm
- "Flexible" → weekday business hours 9am-5pm
- "Anytime this week" → Mon-Fri 9am-5pm
- Empty text → weekday mornings 9am-12pm
""".format(today_date)