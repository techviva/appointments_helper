"""Fetch availability windows from ClickUp archived subtasks."""

import datetime as dt
import re
import urllib
from typing import Optional, Dict, List

import requests
from dateutil import parser as dateparser

from utils.parse_clickup_custom_fields import parse_clickup_task_custom_fields
from utils.ai_utils import get_time_windows_from_availability_text
from utils.cache import refresh_cache_if_stale


from config.app_logging import logger
from config.config import (
    CLICKUP_API_TOKEN,
    CLICKUP_AVAILABILITY_LIST_ID,
)

ISO_DATETIME_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?"
)

def get_clickup_task_by_id(task_id: str) -> Optional[dict]:
    """Fetch a ClickUp task by its ID."""
    if not CLICKUP_API_TOKEN:
        return None

    headers = {"Authorization": CLICKUP_API_TOKEN}
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    response = requests.get(url, headers=headers, timeout=15)
    return response.json()

def _fetch_clickup_availability(days_back:int) -> Dict:
    """Return availability windows for a customer between ``date_from`` and ``date_to``.

    Reads archived subtasks from the configured ClickUp list, pulling windows embedded
    in each subtask's note/description. Supports JSON payloads or raw ISO timestamps.
    """

    if not CLICKUP_API_TOKEN or not CLICKUP_AVAILABILITY_LIST_ID:
        raise ValueError("CLICKUP_API_TOKEN and CLICKUP_AVAILABILITY_LIST_ID must be set.")

    def _safe_parse_unix_timestamp(value: str) -> Optional[dt.datetime]:
        if not value:
            return None
        try:
            return int(dateparser.parse(value).timestamp()*1000)
        except (ValueError, TypeError):
            return None

    start_date = dt.datetime.now().date() - dt.timedelta(days=days_back)
    range_start = _safe_parse_unix_timestamp(start_date)
    

    

    headers = {"Authorization": CLICKUP_API_TOKEN, 
               "accept": "application/json"}
    url = f"https://api.clickup.com/api/v2/list/{CLICKUP_AVAILABILITY_LIST_ID}/task"

    archived_tasks_params = {
        "archived": "true",
        #"subtasks": "true",
        "include_closed": "true",
        "statuses": urllib.parse.parse_qs('"📆 CITA AGENDADA"'),
        "date_created_gt": range_start #if range_start else None,
    }
    

    active_tasks_params = {
        "archived": "false",
        #"subtasks": "true",
        "include_closed": "true",
        "statuses":urllib.parse.parse_qs('"📆 CITA AGENDADA"'),
        "date_created_gt": range_start #if range_start else None,
    }

    
    windows = []
    route_info = []
    page = 0

    logger.info("Fetching availability windows from ClickUp...")
    while True:
        logger.info(f"Fetching page {page} of archived subtasks from ClickUp...")
        archived_tasks_params["page"] = page
        response = requests.get(url, headers=headers, params=archived_tasks_params, timeout=15)

        if response.status_code == 404:
            break
        response.raise_for_status()
        data = response.json()

        #current_tasks_batch = [task for task in data.get("tasks", []) if task.get("name") == "Call notes"]
        #windows += current_tasks_batch
        windows += data.get("tasks", [])

        if data.get("last_page", True):
            break
        page += 1

    page = 0
    while True:
        logger.info(f"Fetching page {page} of active subtasks from ClickUp...")
        active_tasks_params["page"] = page
        response = requests.get(url, headers=headers, params=active_tasks_params, timeout=15)
        if response.status_code == 404:
            break
        response.raise_for_status()
        data = response.json()

        #current_tasks_batch = [task for task in data.get("tasks", []) if task.get("name") == "Call notes"]
        #windows += current_tasks_batch
        windows += data.get("tasks", [])

        if data.get("last_page", True):
            break
        page += 1

    logger.info(f"Fetched {len(windows)} archived subtasks from ClickUp.")
    
    for task in windows:
        parent_id = task.get("parent")
        
        if parent_id:
            parent_task = get_clickup_task_by_id(parent_id)
            custom_fields_data = parse_clickup_task_custom_fields(parent_task)
        else:
            custom_fields_data = parse_clickup_task_custom_fields(task)
        
        
        full_address = " ".join(
                                [
                                 str(custom_fields_data.get("📍 Property Details - Street 1", "Unknown")), 
                                 str(custom_fields_data.get("🏙️ City", "Unknown")),
                                 str(custom_fields_data.get("🏙️ State", "Unknown"))
                                 ]
                                 )
        
        if custom_fields_data.get("📆 Appointment - Start Time") == "" or custom_fields_data.get("📆 Appointment - Start Time") is None:
            is_existing = False
            scheduled_start_date = None
            scheduled_end_date = None
        else:
            is_existing = True
            start_ts = custom_fields_data.get("📆 Appointment - Start Time")
            end_ts = custom_fields_data.get("📆 Appointment - End Time")
            
            # Handle None or empty values
            if start_ts and end_ts:
                scheduled_start_date = dt.datetime.fromtimestamp(int(start_ts) / 1000).isoformat()
                scheduled_end_date = dt.datetime.fromtimestamp(int(end_ts) / 1000).isoformat()
            else:
                is_existing = False
                scheduled_start_date = None
                scheduled_end_date = None


        

        appointment_info = dict(
            address=full_address,
            city=custom_fields_data.get("🏙️ City", "Unknown"),
            #time_windows={"time_windows": []},
            is_existing=is_existing,
            scheduled_start_date=scheduled_start_date,
            scheduled_end_date=scheduled_end_date,
            customer_id=custom_fields_data.get("customer_id", ""),
            customer_name=custom_fields_data.get("customer_name", ""),
        )

        route_info.append(appointment_info)
        logger.info(f"Extracted address and availability windows from ClickUp subtasks - Client {custom_fields_data.get('customer_id','')}.")
        #logger.info(f"Address: {full_address}. Windows: {time_windows['time_windows']}")
    
    
    
    return route_info



def get_clickup_availability(days_back: int = 15) -> List[Dict]:
    """Cached wrapper with idempotent refresh."""
    return refresh_cache_if_stale(
        lambda: _fetch_clickup_availability(days_back)
    )