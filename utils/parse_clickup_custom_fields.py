from typing import List, Dict, Any


target_names = [
                '📆 Appointment - Start Time', 
                '📆 Appointment - End Time', 
                '📍 Property Details - Street 1',
                '🏙️ City',
                '🏙️ State',
                ]


def filter_custom_fields(
    custom_fields: List[Dict[str, Any]], 
    target_names: List[str]
) -> Dict[str, Any]:
    """
    Traverse ClickUp custom_fields and keep only those whose name is in target_names.

    Args:
        custom_fields: list of dicts from ClickUp task JSON under "custom_fields"
        target_names: list of field names to keep

    Returns:
        dict mapping field name -> value (normalized to None if missing)
    """
    # convert to set for O(1) lookups
    target_set = set(target_names)

    filtered = {}
    for field in custom_fields:
        name = field.get("name")
        if name in target_set:
            # Some fields may not have 'value'
            value = field.get("value")
            filtered[name] = value
    return filtered


def parse_clickup_task_custom_fields(task: dict) -> Dict[str, Any]:
    # Minimal demo parser. Expected: "Customer: CUST-010 (Maria Perez). Address: Av. Quito 101, Guayaquil.
    # Availability: 2025-09-17 10:30-12:00, 15:00-17:00 (GMT-5)."
    # For production, implement robust regex/NER or send structured payload from Slack.
    cust_id = task.get('custom_id')
    name = task.get('name')
    customer_appointment_information = filter_custom_fields(task.get('custom_fields'), target_names)
    customer_appointment_information["customer_id"] = cust_id
    customer_appointment_information["customer_name"] = name
    return customer_appointment_information