# policy_config.py
from datetime import time
from zoneinfo import ZoneInfo

# Base / coverage
BASE_ADDR = "10000 N 31st Ave, Phoenix, AZ 85051"
BASE_LATLNG = (33.57486, -112.12765)
COVERAGE_MILES = 65

# Zones
EAST_SIDE_CITIES = {
    "mesa", "chandler", "gilbert", "sun lakes", "queen creek",
    "gold canyon", "apache junction", "san tan valley", "maricopa",
}

# Traffic peaks to avoid for long cross-town hops
PEAK_WINDOWS = [("06:30","08:45"), ("14:00","17:30")]

# Work hours (local)
TZ = ZoneInfo("America/Phoenix")
WEEKDAY_START = time(6, 0)
WEEKDAY_END   = time(17, 0)
SATURDAY_END  = time(13, 0)

# Personnel
RAFAEL_NAME = "Rafael"
RAFAEL_WED_TRAINING = True
RAFAEL_WED_BLOCK = (time(8,30), time(10,30))  # 8:30–10:30
RAFAEL_SAT_CUTOFF = time(13, 0)  # No appointments past 1pm Saturday
RAFAEL_FAMILY_TIME = time(16, 30)  # Must end by 4:30pm for family

# Distance policy buckets (from specification)
EST_MPH = 35.0

# Service duration mappings (from Appointment Times image)
SERVICE_DURATIONS = {
    1: 40,  # 1 service or patio cover
    2: 40,  # 2 services
    3: 55,  # 3 services
    4: 65,  # 4+ services (60-70 range, use 65 as default)
}

def get_service_duration(num_services: int) -> int:
    """Return appointment duration in minutes based on service count."""
    if num_services >= 4:
        return SERVICE_DURATIONS[4]
    return SERVICE_DURATIONS.get(num_services, 40)

# Zone-specific scheduling policies (from coverage map)
ZONE_POLICIES = {
    "High Traffic": {
        "description": "Central Phoenix - Mesa, Tempe, Scottsdale core",
        "weekday_windows": [(time(9, 0), time(13, 0))],  # Mon-Fri 9am-1pm
        "saturday_windows": [(time(7, 0), time(13, 0))],  # Sat 7am-1pm
        "preferred_window_hours": 3,  # Book 2-3 hour windows
        "min_appointments_to_visit": 3,  # Need 3+ to justify fighting traffic
        "defer_days_if_alone": 4,  # If isolated, push 4+ days
        "avoid_peak_travel": True,
    },
    "Medium Traffic": {
        "description": "Mid-range suburbs",
        "weekday_windows": [(time(7, 0), time(14, 0))],  # Mon-Fri 7am-2pm
        "saturday_windows": [(time(7, 0), time(14, 0))],  # Sat 7am-2pm
        "preferred_window_hours": 2,
        "min_appointments_to_visit": 2,
        "defer_days_if_alone": 3,
        "avoid_peak_travel": False,
    },
    "Near Office": {
        "description": "Close to base - quick access",
        "weekday_windows": [(time(9, 0), time(13, 0))],  # Mon-Fri 9am-1pm
        "saturday_windows": [(time(7, 0), time(14, 0))],  # Sat 7am-2pm
        "preferred_window_hours": 2,
        "min_appointments_to_visit": 1,  # Can do solo trips
        "defer_days_if_alone": 0,  # Can schedule same-day/next-day
        "avoid_peak_travel": False,
    },
    "Full Area": {
        "description": "Outer coverage area",
        "weekday_windows": [(time(6, 0), time(17, 0))],  # Full day
        "saturday_windows": [(time(6, 0), time(13, 0))],
        "preferred_window_hours": 2,
        "min_appointments_to_visit": 3,
        "defer_days_if_alone": 4,
        "avoid_peak_travel": True,
    },
}

# Distance-based scheduling rules (from specification section 4.1)
DISTANCE_RULES = {
    "immediate": {
        "max_minutes": 30,
        "policy": "Can schedule same-day or next day if urgent",
        "defer_days": 0,
    },
    "cluster_preferred": {
        "max_minutes": 40,
        "policy": "Ideal to have 3+ appointments in zone same day",
        "defer_days": 2,
        "min_cluster_size": 3,
    },
    "cluster_required": {
        "max_minutes": 60,
        "policy": "Defer 4+ days if no nearby appointments; prefer Saturday",
        "defer_days": 4,
        "min_cluster_size": 2,
        "prefer_saturday": True,
    },
    "accumulate": {
        "max_minutes": 999,  # 75+ miles
        "policy": "Schedule 2-4 weeks out to accumulate zone appointments",
        "defer_days": 14,
        "min_cluster_size": 4,
    },
}

# Daily capacity limits
MAX_APPOINTMENTS_PER_DAY = 8  # With efficient routing
DOUBLE_ROUTE_SPLIT = (3, 3)  # When doing opposite zones (e.g. Queen Creek vs Buckeye)

# Working days
WORKING_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]