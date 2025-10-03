#!/usr/bin/env python3
# main.py
"""
CLI tool to test appointment scheduling system.
"""

import sys
from datetime import datetime
import textwrap
from collections import Counter
from utils.customers_availability import get_clickup_availability
from src.appointment_suggester import suggest_appointments
from utils.ai_utils import get_time_windows_from_availability_text
from config.app_logging import logger


def format_suggestion_output(suggestions: list, customer_address: str):
    """Pretty print scheduling suggestions."""
    print("\n" + "="*80)
    print(f"SCHEDULING SUGGESTIONS FOR: {customer_address}")
    print("="*80 + "\n")
    
    if not suggestions:
        print("❌ No available slots found matching customer availability.\n")
        return
    
    if suggestions[0].get('error'):
        print(f"❌ Error: {suggestions[0]['error']}\n")
        return
    
    for i, sug in enumerate(suggestions, 1):
        print(f"📅 OPTION {i} (Score: {sug['score']:.0f})")
        print(f"   {sug['explanation']}")
        print(f"   📍 Zone: {sug['zone']} ({sug['distance_miles']} mi, ~{sug['travel_minutes']} min from base)")
        print(f"   ⏱️  Duration: {sug['duration_minutes']} minutes")
        print(f"   📊 Appointments in zone that day: {sug['appointments_in_zone']}")
        print()


def test_example_customers():
    """Test with the 10 example customers from requirements."""
    
    examples = [
        {
            "address": "100 W Kesler Ln Chandler, AZ 85225 United States",
            "services": 3,
            "availability": "Flexible weekday mornings until 11am. Tuesdays only after 5pm. Saturdays client is unavailable. Sundays flexible anytime.",
        },
        {
            "address": "112 W Kesler Ln Chandler, AZ 85225 United States",
            "services": 2,
            "availability": "Monday, Wednesday, and Friday available after 4pm. Thursday available all day. Weekends flexible mornings only.",
        },
        {
            "address": "19972 E Vallejo St Queen Creek, AZ 85142 United States",
            "services": 1,
            "availability": "Client prefers appointments only on Mondays and Wednesdays before 2pm. Strict schedule otherwise.",
        },
        {
            "address": "10320 E Catalyst Ave Mesa, AZ 85212 United States",
            "services": 4,
            "availability": "Flexible most weekdays after 3pm. Saturdays available all day. Sundays unavailable.",
        },
        {
            "address": "4098 E Baseline Rd Mesa, AZ 85206 United States",
            "services": 2,
            "availability": "Tuesday, Thursday, and Saturday mornings flexible. Friday strictly available between 12–3pm.",
        },
        {
            "address": "1635 W Inverness Dr Tempe, AZ 85282 United States",
            "services": 1,
            "availability": "Only available Monday through Friday evenings after 6pm. Weekends fully flexible.",
        },
        {
            "address": "17101 N Elko Dr Surprise, AZ 85374 United States",
            "services": 3,
            "availability": "Tuesday and Thursday mornings only. Saturday afternoons flexible. Client unavailable on Sundays.",
        },
        {
            "address": "17478 W Maui Ln Surprise, AZ 85388 United States",
            "services": 2,
            "availability": "Monday through Friday available between 9am–12pm. Client is unavailable evenings and weekends.",
        },
        {
            "address": "19730 N 83rd Dr Peoria, AZ 85382 United States",
            "services": 1,
            "availability": "Flexible most weekdays except Wednesday. Saturday mornings available. Sundays unavailable.",
        },
        {
            "address": "4343 W Sandra Cir Glendale, AZ 85308 United States",
            "services": 4,
            "availability": "Flexible schedule Monday–Friday. Saturday only available before 10am. Sundays strictly unavailable.",
        },
    ]
    
    print("\n🔄 Fetching existing appointments from ClickUp...")
    try:
        existing_appointments = get_clickup_availability(days_back=7)
        print(f"✅ Found {len(existing_appointments)} existing appointments\n")
    except Exception as e:
        print(f"❌ Error fetching appointments: {e}")
        print("⚠️  Proceeding with empty schedule for testing...\n")
        existing_appointments = []

    from collections import Counter
    existing_with_dates = [a for a in existing_appointments if a.get('is_existing') and a.get('scheduled_start_date')]
    print(f"\n🔍 Debug: Appointments with scheduled dates: {len(existing_with_dates)}")
    if existing_with_dates:
        print(f"Sample: {existing_with_dates[0]}")

    today = datetime.now().date()
    dates = []
    for a in existing_appointments:
        if a.get('scheduled_start_date'):
            try:
                dt = datetime.fromisoformat(a['scheduled_start_date'].replace('Z', '+00:00'))
                if dt.date() >= today:  # Only future dates
                    dates.append(dt.strftime('%Y-%m-%d'))
            except:
                pass
    date_counts = Counter(dates)
    print(f"Top dates: {dict(list(date_counts.most_common(7)))}\n")
    
    # Test first 3 examples
    for example in examples:
        print("\n" + "━"*80)
        print(f"Testing: {example['address']}")
        print(f"Services: {example['services']}")
        print("Customer Availability: ")
        print(textwrap.fill(example['availability'], width=78))
        print("━"*80)
        
        try:
            # Parse availability with AI
            time_windows = get_time_windows_from_availability_text(example['availability'])
            
            # Build request
            request = {
                'address': example['address'],
                'services': example['services'],
                'time_windows': time_windows['time_windows'],
                'city': example['address'].split(',')[1].strip() if ',' in example['address'] else '',
            }
            
            # Get suggestions
            suggestions = suggest_appointments(request, existing_appointments)
            
            # Display results
            format_suggestion_output(suggestions, example['address'])
            
        except Exception as e:
            print(f"\n❌ Error processing request: {e}\n")
            import traceback
            traceback.print_exc()


def test_single_address():
    """Interactive mode - test a single address."""
    print("\n" + "="*80)
    print("SINGLE ADDRESS TESTING MODE")
    print("="*80 + "\n")
    
    address = input("Enter customer address: ").strip()
    if not address:
        print("❌ Address required")
        return
    
    services = input("Number of services (1-4+): ").strip()
    try:
        services = int(services)
    except ValueError:
        services = 1
    
    availability = input("Customer availability (natural language): ").strip()
    if not availability:
        availability = "Flexible weekdays 9am-5pm"
    
    print("\n🔄 Fetching existing appointments from ClickUp...")
    try:
        existing_appointments = get_clickup_availability(days_back=15)
        print(f"✅ Found {len(existing_appointments)} existing appointments\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        existing_appointments = []
    
    try:
        # Parse availability
        time_windows = get_time_windows_from_availability_text(availability)
        
        request = {
            'address': address,
            'services': services,
            'time_windows': time_windows['time_windows'],
            'city': address.split(',')[1].strip() if ',' in address else '',
        }
        
        suggestions = suggest_appointments(request, existing_appointments)
        format_suggestion_output(suggestions, address)
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "🚀 "+"="*76)
    print("   ROUTE OPTIMIZATION - APPOINTMENT SCHEDULER")
    print("="*78 + " 🚀\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        test_single_address()
    else:
        print("Testing with example customers from requirements...\n")
        test_example_customers()
        
        print("\n" + "="*80)
        print("💡 To test a custom address, run: python main.py --single")
        print("="*80 + "\n")