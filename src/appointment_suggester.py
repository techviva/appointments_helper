# appointment_suggester.py
from datetime import datetime, timedelta, time
from typing import List, Dict, Tuple, Optional
from zoneinfo import ZoneInfo

from config.policy_config import (
    ZONE_POLICIES, DISTANCE_RULES, BASE_LATLNG, EST_MPH,
    RAFAEL_WED_BLOCK, RAFAEL_SAT_CUTOFF, RAFAEL_FAMILY_TIME,
    WEEKDAY_START, WEEKDAY_END, SATURDAY_END, TZ, EAST_SIDE_CITIES,
    get_service_duration, WORKING_DAYS, MAX_APPOINTMENTS_PER_DAY
)
from utils.haversine_distance import haversine_miles, estimate_minutes_from_base
from utils.city_quadrants import classify_zone
from utils.address_geocoding import geocode_address


def parse_availability_windows(time_windows: List[Dict]) -> List[Tuple[datetime, datetime]]:
    """Convert time_windows from AI parsing into datetime tuples."""
    windows = []
    for window in time_windows:
        try:
            start = datetime.fromisoformat(window['start'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(window['end'].replace('Z', '+00:00'))
            # Convert to Phoenix timezone
            start = start.astimezone(TZ)
            end = end.astimezone(TZ)
            windows.append((start, end))
        except (KeyError, ValueError) as e:
            continue
    return windows


def get_distance_policy(minutes_from_base: int) -> Dict:
    """Determine scheduling policy based on travel time from base."""
    for policy_name, policy in DISTANCE_RULES.items():
        if minutes_from_base <= policy['max_minutes']:
            return policy
    return DISTANCE_RULES['accumulate']


def count_appointments_in_zone(existing_appointments: List[Dict], zone_label: str, target_date: datetime) -> int:
    """Count how many appointments are already scheduled in this zone on target_date."""
    count = 0
    for appt in existing_appointments:
        if not appt.get('is_existing'):
            continue
        
        # Parse scheduled start date
        try:
            appt_start = datetime.fromisoformat(appt['scheduled_start_date'].replace('Z', '+00:00'))
            appt_start = appt_start.astimezone(TZ)
        except:
            continue
        
        # Check if same day
        if appt_start.date() != target_date.date():
            continue
        
        # Check if same zone
        lat, lon = geocode_address(appt['address'])
        if lat and lon:
            appt_zone = classify_zone(lat, lon)
            if appt_zone == zone_label:
                count += 1
    
    return count


def is_time_slot_available(candidate_dt: datetime, duration_minutes: int, 
                           existing_appointments: List[Dict]) -> bool:
    """Check if a time slot is free (no conflicts with existing appointments)."""
    candidate_end = candidate_dt + timedelta(minutes=duration_minutes)
    
    for appt in existing_appointments:
        if not appt.get('is_existing'):
            continue
        
        try:
            appt_start = datetime.fromisoformat(appt['scheduled_start_date'].replace('Z', '+00:00'))
            appt_end = datetime.fromisoformat(appt['scheduled_end_date'].replace('Z', '+00:00'))
            appt_start = appt_start.astimezone(TZ)
            appt_end = appt_end.astimezone(TZ)
        except:
            continue
        
        # Check for overlap
        if not (candidate_end <= appt_start or candidate_dt >= appt_end):
            return False
    
    return True


def check_rafael_constraints(dt: datetime) -> bool:
    """Check if datetime violates Rafael's personal constraints."""
    # Wednesday training block
    if dt.weekday() == 2:  # Wednesday
        if RAFAEL_WED_BLOCK[0] <= dt.time() <= RAFAEL_WED_BLOCK[1]:
            return False
    
    # Saturday cutoff
    if dt.weekday() == 5:  # Saturday
        if dt.time() > RAFAEL_SAT_CUTOFF:
            return False
    
    # Family time cutoff (all days)
    if dt.time() >= RAFAEL_FAMILY_TIME:
        return False
    
    return True


def generate_candidate_slots(zone_label: str, customer_windows: List[Tuple[datetime, datetime]], 
                             duration_minutes: int, defer_days: int = 0) -> List[datetime]:
    """Generate candidate appointment slots based on zone policy and customer availability."""
    zone_policy = ZONE_POLICIES.get(zone_label, ZONE_POLICIES["Full Area"])
    candidates = []
    
    now = datetime.now(TZ)
    start_date = now.date() + timedelta(days=defer_days)
    end_date = start_date + timedelta(days=14)  # Look 2 weeks ahead
    
    current = datetime.combine(start_date, time(6, 0), tzinfo=TZ)
    
    while current.date() <= end_date:
        # Check if working day
        day_name = current.strftime("%A")
        if day_name not in WORKING_DAYS:
            current += timedelta(days=1)
            continue
        
        # Get zone's allowed windows for this day
        is_saturday = current.weekday() == 5
        allowed_windows = zone_policy['saturday_windows'] if is_saturday else zone_policy['weekday_windows']
        
        for window_start, window_end in allowed_windows:
            slot_time = datetime.combine(current.date(), window_start, tzinfo=TZ)
            window_end_dt = datetime.combine(current.date(), window_end, tzinfo=TZ)
            
            # Generate 30-minute interval slots within window
            while slot_time + timedelta(minutes=duration_minutes) <= window_end_dt:
                # Check if slot falls within customer availability
                for cust_start, cust_end in customer_windows:
                    slot_end = slot_time + timedelta(minutes=duration_minutes)
                    if cust_start <= slot_time and slot_end <= cust_end:
                        # Check Rafael constraints
                        if check_rafael_constraints(slot_time):
                            candidates.append(slot_time)
                
                slot_time += timedelta(minutes=30)
        
        current += timedelta(days=1)
    
    return candidates


def score_appointment_option(candidate_dt: datetime, zone_label: str, 
                             appointments_in_zone: int, distance_policy: Dict,
                             is_east_side: bool, total_on_day: int) -> Tuple[float, str]:
    """Score an appointment option and generate explanation."""
    score = 100.0
    reasons = []
    
    # Proximity bonus
    days_out = (candidate_dt.date() - datetime.now(TZ).date()).days
    if days_out == 0:
        score += 50
        reasons.append("same-day service")
    elif days_out == 1:
        score += 30
        reasons.append("next-day service")
    elif days_out == 2:
        score += 20
        reasons.append("2 days out")
    elif days_out == 3:
        score += 10
        reasons.append("3 days out")
    
    # Grouping bonus - REDUCED from 25 to 15 per appointment
    if appointments_in_zone > 0:
        bonus = appointments_in_zone * 15
        score += bonus
        reasons.append(f"grouped with {appointments_in_zone} other appointment(s) in {zone_label}")
    
    # Penalize over-concentrated days
    if total_on_day >= 6:
        penalty = (total_on_day - 5) * 10
        score -= penalty
        reasons.append(f"⚠️ busy day ({total_on_day} appointments already)")
    
    # Saturday preference for far zones
    if candidate_dt.weekday() == 5 and distance_policy.get('prefer_saturday'):
        score += 20
        reasons.append("Saturday (less traffic for distant location)")
    
    # East side special handling
    if is_east_side and appointments_in_zone >= 2:
        score += 15
        reasons.append("efficient East Side cluster")
    
    # Penalize isolated trips to far zones
    min_cluster = distance_policy.get('min_cluster_size', 1)
    if appointments_in_zone < min_cluster:
        penalty = (min_cluster - appointments_in_zone) * 15
        score -= penalty
        if min_cluster > 1:
            reasons.append(f"⚠️ solo trip (ideally {min_cluster}+ appointments in zone)")
    
    # Time of day preference (morning slightly better)
    if 7 <= candidate_dt.hour <= 10:
        score += 5
        reasons.append("morning slot")
    
    explanation = f"{candidate_dt.strftime('%A, %B %d at %I:%M %p')} - " + "; ".join(reasons)
    
    return score, explanation


def count_appointments_on_date(existing_appointments: List[Dict], target_date: datetime) -> int:
    """Count total appointments scheduled on a specific date."""
    count = 0
    for appt in existing_appointments:
        if not appt.get('is_existing'):
            continue
        try:
            appt_start = datetime.fromisoformat(appt['scheduled_start_date'].replace('Z', '+00:00'))
            appt_start = appt_start.astimezone(TZ)
            if appt_start.date() == target_date.date():
                count += 1
        except:
            continue
    return count


def suggest_appointments(new_request: Dict, existing_appointments: List[Dict]) -> List[Dict]:
    """
    Main scheduling engine.
    
    Args:
        new_request: {
            'address': str,
            'services': int,
            'time_windows': List[Dict] with 'start' and 'end' ISO strings
        }
        existing_appointments: List from ClickUp with scheduled appointments
        
    Returns:
        List of suggestion dicts with 'datetime', 'score', 'explanation'
    """
    
    # 1. Geocode and classify
    lat, lon = geocode_address(new_request['address'])
    if not lat or not lon:
        return [{"error": "Could not geocode address"}]
    
    zone_label = classify_zone(lat, lon)
    distance_miles = haversine_miles(lat, lon)
    minutes_from_base = estimate_minutes_from_base(lat, lon)
    
    # 2. Determine policies
    distance_policy = get_distance_policy(minutes_from_base)
    service_duration = get_service_duration(new_request['services'])
    
    # 3. Check if East Side
    city = new_request.get('city', '').lower()
    is_east_side = city in EAST_SIDE_CITIES or zone_label == "High Traffic"
    
    # 4. Parse customer availability
    customer_windows = parse_availability_windows(new_request['time_windows'])
    if not customer_windows:
        return [{"error": "No valid availability windows found"}]
    
    # 5. Generate candidate slots based on distance policy
    defer_days = distance_policy.get('defer_days', 0)
    candidates = generate_candidate_slots(zone_label, customer_windows, service_duration, defer_days)
    
    if not candidates:
        # Relax defer constraint and try immediate scheduling
        candidates = generate_candidate_slots(zone_label, customer_windows, service_duration, defer_days=0)
    
    # 6. Score and filter candidates
    suggestions = []
    for candidate_dt in candidates[:100]:  # Evaluate more slots for diversity
        # Check availability (no conflicts)
        if not is_time_slot_available(candidate_dt, service_duration, existing_appointments):
            continue
        
        # Check daily capacity - don't overload any single day
        total_on_day = count_appointments_on_date(existing_appointments, candidate_dt)
        if total_on_day >= MAX_APPOINTMENTS_PER_DAY:
            continue  # Skip this slot, day is full
        
        # Count appointments in same zone on same day
        appts_in_zone = count_appointments_in_zone(existing_appointments, zone_label, candidate_dt)
        
        # Score this option
        score, explanation = score_appointment_option(
            candidate_dt, zone_label, appts_in_zone, distance_policy, is_east_side, total_on_day
        )
        
        suggestions.append({
            'datetime': candidate_dt,
            'date': candidate_dt.strftime('%Y-%m-%d'),
            'time': candidate_dt.strftime('%I:%M %p'),
            'day_of_week': candidate_dt.strftime('%A'),
            'score': score,
            'explanation': explanation,
            'zone': zone_label,
            'distance_miles': round(distance_miles, 1),
            'travel_minutes': minutes_from_base,
            'duration_minutes': service_duration,
            'appointments_in_zone': appts_in_zone,
            'total_appointments_that_day': total_on_day,
        })
    
    # 7. Sort by score and enforce day diversity
    suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    # Ensure we suggest different days (not all Saturday)
    diverse_suggestions = []
    seen_dates = set()
    
    for sug in suggestions:
        if sug['date'] not in seen_dates:
            diverse_suggestions.append(sug)
            seen_dates.add(sug['date'])
            if len(diverse_suggestions) >= 3:
                break
    
    # If we don't have 3 different days, fill with best remaining options
    if len(diverse_suggestions) < 3:
        for sug in suggestions:
            if sug not in diverse_suggestions:
                diverse_suggestions.append(sug)
                if len(diverse_suggestions) >= 3:
                    break
    
    return diverse_suggestions[:3]