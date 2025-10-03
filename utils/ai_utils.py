import json
import time

# pip install google-generativeai python-dateutil pydantic google-api-python-client google-auth requests
from google import genai
from google.genai.errors import ServerError
from google.genai import types


from config.ai_config import PARSE_NOTE_PROMPT
from config.config import GEMINI_API_KEY
from config.app_logging import logger



def get_time_windows_from_availability_text(slack_text: str, horizon_days: int = 3):
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = ai_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[PARSE_NOTE_PROMPT, slack_text]
            )
            
            parsed_time_windows = json.loads(response.text.replace("json","").replace("```",""))
            
            # Check if we got valid windows
            if parsed_time_windows.get('time_windows') and len(parsed_time_windows['time_windows']) > 0:
                return parsed_time_windows
            
            # Empty result - log and retry with backoff
            logger.warning(f"Attempt {attempt + 1}: AI returned empty time_windows for: {slack_text[:100]}")
            if attempt < max_attempts - 1:  # Don't sleep on last attempt
                time.sleep(2 ** attempt)
            
        except ServerError as e:
            logger.error(f"Attempt {attempt + 1}: Server error: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)
        except json.JSONDecodeError as e:
            logger.error(f"Attempt {attempt + 1}: JSON parsing failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)
    
    # All retries failed - use default
    logger.warning(f"All {max_attempts} AI attempts failed for text: {slack_text[:100]}. Using default availability.")
    from datetime import datetime, timedelta
    default_windows = []
    for i in range(1, 8):
        date = datetime.now().date() + timedelta(days=i)
        if date.weekday() < 5:
            default_windows.append({
                'start': f"{date.isoformat()}T09:00:00-07:00",
                'end': f"{date.isoformat()}T12:00:00-07:00"
            })
    return {'time_windows': default_windows}