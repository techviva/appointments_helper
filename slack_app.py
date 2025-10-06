# slack_app.py
import os
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from fastapi import FastAPI, Request
from utils.ai_utils import get_time_windows_from_availability_text
from utils.customers_availability import get_clickup_availability
from src.appointment_suggester import suggest_appointments  # adjust if your module path differs
from datetime import datetime, timedelta


SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
api = FastAPI()
handler = SlackRequestHandler(app)




def calculate_time_window_hours(time_windows: list) -> int:
    """
    Determine if customer needs 2 or 3 hour appointment window.
    
    Returns: 2 or 3 (hours)
    """
    if not time_windows:
        return 2  # Default to shorter window if unknown
    
    # Calculate total available hours
    total_hours = 0
    for window in time_windows:
        try:
            start = datetime.fromisoformat(window['start'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(window['end'].replace('Z', '+00:00'))
            total_hours += (end - start).total_seconds() / 3600
        except:
            continue
    
    num_windows = len(time_windows)
    
    # Heuristic:
    # - If customer has 15+ hours available across 1-3 windows → Very flexible → 3 hours
    # - If customer has < 8 hours OR 5+ fragmented windows → Constrained → 2 hours
    
    if total_hours >= 15 and num_windows <= 3:
        return 3  # Flexible customer
    elif total_hours < 8 or num_windows >= 5:
        return 2  # Constrained/picky customer
    else:
        return 2  # Default to 2 hours (safer)



def format_blocks(suggestions, address, cust_time_windows):
    if not suggestions:
        return [{"type":"section","text":{"type":"mrkdwn","text":f"❌ No options for *{address}*"}}]
    blocks = [{"type":"section","text":{"type":"mrkdwn","text":f"*Appointment suggestions for:* `{address}`"}}]

    window_hours = calculate_time_window_hours(cust_time_windows)
    for i, s in enumerate(suggestions, 1):
        t_as_time = datetime.strptime(s['time'], "%I:%M %p")
        end_time = t_as_time + timedelta(hours=window_hours)
        end_time_str = end_time.strftime("%I:%M %p")
        line = f"*Option {i}* — *{s['day_of_week']}* {s['date']} at *{s['time']}:{end_time_str} - window: {window_hours} hours*\n{s['explanation']}\n Zone: *{s['zone']}* *travel time*:~{s['travel_minutes']} min *distance*: {s['distance_miles']} miles *service duration*: {s['duration_minutes']} min"
        blocks += [{"type":"divider"},{"type":"section","text":{"type":"mrkdwn","text":line}}]
    return blocks

@app.command("/suggest")
def handle_suggest(ack, respond, command, logger):
    # Ack fast so Slack doesn’t time out
    ack(response_type="ephemeral", text="Working on it…")
    try:
        # Expect: address | services | availability
        text = command.get("text","")
        parts = [p.strip() for p in text.split("|")]
        address = parts[0]
        services = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        availability = parts[2] if len(parts) > 2 else "Flexible weekdays 9am-5pm"

        time_windows = get_time_windows_from_availability_text(availability)
        req = {
            "address": address,
            "services": services,
            "time_windows": time_windows["time_windows"],
            "city": address.split(",")[1].strip() if "," in address else "",
        }

        existing = get_clickup_availability(days_back=15)
        suggestions = suggest_appointments(req, existing)
        respond(blocks=format_blocks(suggestions, address, time_windows["time_windows"]))
    except Exception as e:
        logger.exception(e)
        respond(response_type="ephemeral", text=f"❌ Error: {e}")

@api.post("/slack/events")
async def slack_events(req: Request):
    return await handler.handle(req)

@api.get("/healthz")
def healthz():
    return {"ok": True}
