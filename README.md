# 🚀 Intelligent Route Optimization & Appointment Scheduler

> AI-powered appointment scheduling system that optimizes routes, clusters appointments by geographic zones, and respects business constraints to maximize field technician efficiency.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Installation](#installation)
  - [Local Development](#local-development)
  - [Production Server Deployment](#production-server-deployment)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Slack Commands](#slack-commands)
  - [CLI Testing](#cli-testing)
- [Codebase Structure](#codebase-structure)
- [How It Works](#how-it-works)
- [Performance](#performance)
- [License](#license)

---

## Overview

This system solves the complex problem of scheduling field service appointments across a large metropolitan area (Phoenix, AZ) while optimizing for:

- **Geographic clustering** - Group appointments in the same zone on the same day
- **Traffic patterns** - Avoid high-traffic hours and areas
- **Customer availability** - Natural language parsing of scheduling constraints
- **Technician capacity** - Daily appointment limits and personal constraints
- **Business policies** - Zone-specific time windows and distance-based scheduling rules

The system integrates with **ClickUp** for appointment management and **Slack** for real-time scheduling suggestions during customer calls.

---

## Key Features

### 🎯 Intelligent Scheduling
- **Zone-based routing** - Divides service area into High Traffic, Medium Traffic, Near Office, and Full Area zones
- **Distance-aware policies** - Automatically applies deferral rules based on travel time
- **Clustering optimization** - Groups appointments in the same zone to minimize travel
- **Conflict detection** - Prevents double-booking and overloading schedules

### 🗺️ Geographic Intelligence
- **Automated zone classification** - Uses GeoJSON polygons to classify customer locations
- **Traffic-aware scheduling** - Avoids peak traffic hours (6:30-8:45am, 2:00-5:30pm)
- **Distance calculation** - Haversine distance from base location with travel time estimates

### 🤖 AI-Powered Availability Parsing
- **Natural language processing** - Converts customer availability text into structured time windows
- **Fallback handling** - Provides default availability if AI parsing fails
- **Multiple retry logic** - Exponential backoff for API errors

### ⚡ Performance Optimization
- **File-based caching** - 1-hour cache with atomic writes and file locking
- **Idempotent refresh** - Prevents duplicate API calls during concurrent access
- **Sub-second response times** - Cached data returns in < 2 seconds

### 📊 Business Rules Enforcement
- **Zone time window restrictions** - Enforces company policies on service hours by zone
- **Daily capacity limits** - Prevents overloading technicians (8 appointments/day max)
- **Technician constraints** - Respects personal schedules (Wednesday training, Saturday 1pm cutoff, family time 4:30pm)
- **Service duration logic** - Adjusts appointment length based on number of services (40-65 minutes)

---

## System Architecture

```
┌─────────────────┐
│  Slack Message  │ ← Customer calls, availability shared
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Slack App (slack_app.py)                           │
│  • Receives /suggest command                        │
│  • Parses customer info                             │
│  • Calls suggestion engine                          │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Appointment Suggester (appointment_suggester.py)   │
│  • Geocodes address                                 │
│  • Classifies zone                                  │
│  • Applies business rules                           │
│  • Scores options                                   │
└────────┬────────────────────────────────────────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
    ┌────────┐    ┌─────────┐   ┌──────────┐   ┌─────────┐
    │ ClickUp│    │ Google  │   │  Gemini  │   │  Cache  │
    │   API  │    │ Maps API│   │ AI (NLP) │   │  (JSON) │
    └────────┘    └─────────┘   └──────────┘   └─────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Slack Response                                     │
│  • Top 3 suggestions with scores                    │
│  • Zone info, travel time, clustering details       │
│  • Policy conflict warnings if applicable           │
└─────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.11+
- Ubuntu/Debian server (for production deployment)
- ClickUp account with API access
- Google Maps API key
- Google Gemini API key
- Slack workspace with app creation permissions

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/techviva/appointments_helper.git
   cd appointments_helper
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Required variables:
   ```env
   # Google APIs
   GOOGLE_MAPS_API_KEY=your_maps_api_key
   GEMINI_API_KEY=your_gemini_api_key
   PROJECT_ID=your_gcp_project_id
   
   # ClickUp
   CLICKUP_API_TOKEN=your_clickup_token
   CLICKUP_AVAILABILITY_LIST_ID=your_list_id
   
   # Slack
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_SIGNING_SECRET=your_signing_secret
   
   # Optional
   SERVICE_ACCOUNT_FILE=path/to/service-account.json
   ```

5. **Initialize cache directory**
   ```bash
   mkdir -p cache logs
   ```

6. **Test CLI (without Slack)**
   ```bash
   python main.py
   ```
   This tests the core scheduling engine with example customers.

---

### Production Server Deployment

#### 1. Server Setup (Ubuntu 22.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and dependencies
sudo apt install python3.11 python3.11-venv python3-pip nginx -y

# Create application user
sudo useradd -m -s /bin/bash appuser
sudo su - appuser
```

#### 2. Deploy Application

```bash
# Clone repository
cd /home/appuser
git clone https://github.com/techviva/appointments_helper.git
cd appointments_helper

# Set up virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
nano .env  # Add production credentials

# Create necessary directories
mkdir -p cache logs
```

#### 3. Systemd Service Configuration

Create systemd service file:
```bash
sudo nano /etc/systemd/system/appointments_helper.service
```

```ini
[Unit]
Description=Route Optimization Slack App
After=network.target

[Service]
Type=notify
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/appointments_helper
Environment="PATH=/home/appuser/appointments_helper/venv/bin"
ExecStart=/home/appuser/appointments_helper/venv/bin/uvicorn slack_app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log

# Restart policy
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable appointments_helper.service
sudo systemctl start appointments_helper.service
sudo systemctl status appointments_helper.service
```

#### 4. Nginx Reverse Proxy

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/appointments_helper
```

```nginx
upstream route_optimizer {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Slack webhook endpoint
    location /slack/events {
        proxy_pass http://appointments_helper;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Slack requires response within 3 seconds
        proxy_connect_timeout 3s;
        proxy_send_timeout 3s;
        proxy_read_timeout 3s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://appointments_helper;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/appointments_helper-access.log;
    error_log /var/log/nginx/appointments_helper-error.log;
}
```

Enable site and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/appointments_helper /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. SSL Configuration (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
sudo systemctl reload nginx
```

#### 6. Firewall Configuration

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

#### 7. Monitoring & Logs

```bash
# View application logs
sudo journalctl -u appointments_helper.service -f

# View Nginx logs
sudo tail -f /var/log/nginx/appointments_helper-error.log

# Check service status
sudo systemctl status appointments_helper.service
```

---

## Configuration

### Zone Definitions (`config/zones.geojson`)

The system uses GeoJSON polygons to define service zones:

```json
{
  "type": "Feature",
  "properties": {
    "id": "high_traffic",
    "label": "High Traffic",
    "zone_order": 1
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [...]
  }
}
```

### Policy Configuration (`config/policy_config.py`)

Business rules and constraints:

```python
# Zone-specific scheduling windows
ZONE_POLICIES = {
    "High Traffic": {
        "weekday_windows": [(time(9, 0), time(13, 0))],  # 9am-1pm
        "saturday_windows": [(time(7, 0), time(13, 0))],  # 7am-1pm
        "min_appointments_to_visit": 3,
        "defer_days_if_alone": 4,
    }
}

# Distance-based rules
DISTANCE_RULES = {
    "immediate": {"max_minutes": 30, "defer_days": 0},
    "cluster_preferred": {"max_minutes": 40, "defer_days": 2},
    "cluster_required": {"max_minutes": 60, "defer_days": 4},
}

# Service duration
SERVICE_DURATIONS = {1: 40, 2: 40, 3: 55, 4: 65}

# Personnel constraints
RAFAEL_WED_TRAINING = (time(8, 30), time(10, 30))
RAFAEL_SAT_CUTOFF = time(13, 0)
RAFAEL_FAMILY_TIME = time(16, 30)
```

---

## Usage

### Slack Commands

#### 1. Set up Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Enable **Slash Commands** and create `/suggest` command
3. Set **Request URL** to: `https://appointments-helper.mooo.com/slack/events`
4. Enable **Interactivity** with same URL
5. Add **OAuth Scopes**: `commands`, `chat:write`, `users:read`
6. Install app to workspace and copy **Bot Token** to `.env`

#### 2. Using `/suggest` Command

In any Slack channel:

```
/suggest Address | n services | Availability

/suggest 100 W Kesler Ln Chandler, AZ 85225 | 3 | Flexible weekday mornings until 11am. Tuesdays only after 5pm.
```

**Response format:**
```
📅 OPTION 1 (Score: 165) — Saturday Oct 4 at 11:00 AM - 2:00 PM
   • Grouped with 2 other appointments in High Traffic zone
   • 25.5 mi from base (~48 min travel)
   • 55 minute appointment

📅 OPTION 2 (Score: 105) — Monday Oct 6 at 9:00 AM - 11:00 AM
   • Solo trip (ideally 2+ appointments in zone)
   • Morning slot available
```

#### 3. Policy Conflict Warnings

If customer availability doesn't match zone policies:

```
⚠️ Scheduling Conflict - High Traffic Zone Restrictions

Customer availability does not match service windows for High Traffic zone.

Zone Policy:
  • Weekdays: 09:00AM-01:00PM
  • Saturdays: 07:00AM-01:00PM

Customer requested times fall outside these windows due to traffic/operational policies.
```

### CLI Testing

Test the scheduling engine without Slack:

```bash
# Run with example customers
python main.py

# Test single custom address
python main.py --single
```

---

## Codebase Structure

```
route-optimization/
├── config/
│   ├── ai_config.py          # AI prompts and tool definitions
│   ├── app_logging.py        # Centralized logging configuration
│   ├── config.py             # Environment variable loading
│   ├── policy_config.py      # Business rules and zone policies
│   └── zones.geojson         # Geographic zone definitions
│
├── services/
│   └── appointment_suggester.py   # Core scheduling engine
│
├── utils/
│   ├── address_geocoding.py       # Google Maps API wrapper
│   ├── ai_utils.py                # Gemini AI availability parsing
│   ├── cache.py                   # File-based caching with locking
│   ├── city_quadrants.py          # Zone classification logic
│   ├── customers_availability.py  # ClickUp API integration
│   ├── haversine_distance.py      # Distance calculations
│   └── parse_clickup_custom_fields.py  # ClickUp field parsing
│
├── cache/                     # Cached ClickUp data (gitignored)
├── logs/                      # Application logs (gitignored)
├── main.py                    # CLI testing interface
├── slack_app.py               # Slack bot application
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (gitignored)
└── README.md                  # This file
```

### Key Files Explained

#### `appointment_suggester.py` - Core Scheduling Logic
- **Geocoding & Classification**: Converts address to lat/lon, determines zone
- **Policy Application**: Applies distance rules and zone restrictions
- **Candidate Generation**: Creates possible appointment slots within customer availability
- **Conflict Detection**: Checks for scheduling conflicts with existing appointments
- **Scoring Algorithm**: Ranks options by proximity, clustering, and efficiency
- **Day Diversity**: Ensures suggestions span multiple days

**Scoring Weights:**
- Proximity: +50 (same day), +30 (next day), +20 (2 days), +10 (3 days)
- Clustering: +15 per appointment in zone
- Saturday bonus (far zones): +20
- East Side cluster: +15
- Morning slot: +5
- Over-capacity penalty: -10 per appointment over 5
- Isolated trip penalty: -15 per missing appointment

#### `customers_availability.py` - ClickUp Integration
- Fetches "Call notes" subtasks from ClickUp
- Parses parent task custom fields (address, appointment dates)
- Converts Unix timestamps to ISO format
- **Optimization**: Only parses availability for unscheduled customers (not existing appointments)
- Returns structured data for scheduling engine

#### `cache.py` - Performance Optimization
- **File-based caching** with 1-hour TTL
- **Atomic writes** using temp files + rename (prevents corruption)
- **File locking** via `fcntl` (prevents duplicate fetches)
- **Idempotent refresh**: Multiple simultaneous calls result in single fetch

#### `city_quadrants.py` - Geographic Classification
- Loads GeoJSON zone polygons using Shapely
- Point-in-polygon check to determine zone
- Returns: "High Traffic", "Medium Traffic", "Near Office", "Full Area", or "unclassified"

#### `ai_utils.py` - Natural Language Processing
- Uses Google Gemini 2.0 Flash for availability parsing
- Converts free-text like "Flexible weekday mornings" → structured time windows
- Retry logic with exponential backoff
- Fallback to default availability (weekday mornings) if parsing fails

#### `slack_app.py` - Slack Integration
- FastAPI application handling `/suggest` slash command
- Parses Slack modal submissions
- Calls scheduling engine
- Formats response with interactive blocks
- Calculates 2-3 hour appointment windows based on customer flexibility

---

## How It Works

### End-to-End Flow

1. **Customer calls company** → Sales team notes availability in Slack
2. **Sales team triggers `/suggest`** → Slack modal opens
3. **Enter customer details**:
   - Address (geocoded automatically)
   - Number of services (determines appointment duration)
   - Availability in natural language
4. **System processes request**:
   - Geocodes address → determines zone
   - Parses availability with AI → structured time windows
   - Loads existing appointments from cache (< 2 seconds if fresh)
   - Applies business rules (zone policies, distance rules)
   - Generates candidate slots
   - Checks for conflicts
   - Scores each option
   - Returns top 3 diverse suggestions
5. **Sales team presents options** → Customer selects preferred time
6. **Appointment scheduled** → Added to ClickUp (manually for now)

### Special Business Rules

**High Traffic Zone Exception:**
- Normal rule: Defer appointments 2-4 days, require clustering
- Exception: If distance < 40 minutes, allow next-day scheduling
- Rationale: Close locations don't need clustering to be efficient

**Zone Time Windows:**
- Enforced to avoid traffic congestion
- Customer availability must overlap with zone windows
- Clear error message if incompatible

**East Side Special Handling:**
- Cities: Mesa, Chandler, Gilbert, Queen Creek, etc.
- Encourages clustering (bonus points for 2+ appointments)
- Prefers Saturday for better traffic conditions

---

## Performance

### Caching Impact

| Scenario | Without Cache | With Cache (Fresh) | Improvement |
|----------|--------------|-------------------|-------------|
| First request | 18 seconds | 18 seconds | N/A |
| Subsequent requests (< 1 hour) | 18 seconds | < 2 seconds | **99.8% faster** |
| Concurrent requests | 2× 18 seconds | 1× 18 seconds + 2 sec | **50% reduction** |

### API Call Optimization

| Component | Calls Per Request | Notes |
|-----------|------------------|-------|
| ClickUp API | 0 (cached) or 100+ (fresh) | Fetches 338 appointments |
| Google Maps Geocoding | 1 | Per new customer address |
| Gemini AI | 1 | Availability parsing only |

### Scalability

- **Cache TTL**: 1 hour (configurable in `cache.py`)
- **Concurrent safety**: File locking prevents race conditions
- **Worker processes**: 4 Uvicorn workers (configurable in systemd)
- **Response time SLA**: < 3 seconds (Slack requirement)

---

## License

**Copyright © 2025 Viva Landscape & Design. All Rights Reserved.**

This software and associated documentation files (the "Software") are proprietary and confidential. Unauthorized copying, modification, distribution, or use of this Software, via any medium, is strictly prohibited without explicit written permission from Viva Landscape & Design.

**Terms:**
- The Software is licensed, not sold
- No part of the Software may be reproduced, distributed, or transmitted in any form
- Reverse engineering, decompilation, or disassembly is prohibited
- This license is personal and non-transferable

For licensing inquiries, contact: [tech@vivalandscapedesign.com]

---

## Support & Maintenance

**For issues or questions:**
- Internal team: Slack #appointments-suggest channel
- Technical support: tech@vivalandscapedesign.com


**Maintenance schedule:**
- Cache refresh: Automatic every hour
- ClickUp sync: Real-time during calls
- Server updates: Monthly security patches
- Monitoring: 24/7 via systemd + Nginx logs

---

## Roadmap

### Planned Features
- [ ] Automatic ClickUp appointment creation (eliminate manual step)
- [ ] Real-time traffic data integration
- [ ] Multi-technician optimization
- [ ] Interactive map visualization
- [ ] Mobile app for technicians


### Recently Completed
- [x] Zone-based geographic classification
- [x] AI-powered availability parsing
- [x] File-based caching with locking
- [x] Slack integration
- [x] Business rules engine
- [x] Scoring algorithm with clustering optimization

---

**Built with ❤️ to optimize field service operations**