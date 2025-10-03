# utils/cache.py
import json
import os
import fcntl
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "clickup_appointments.json"
LOCK_FILE = CACHE_DIR / "clickup.lock"
CACHE_DURATION_HOURS = 1

def _acquire_lock(lock_path: Path, timeout: int = 10) -> int:
    """Acquire exclusive lock with timeout."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        # Lock held by another process - wait and use existing cache
        os.close(lock_fd)
        return None

def _release_lock(lock_fd: int):
    """Release lock."""
    if lock_fd is not None:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)

def save_clickup_cache(data: List[Dict]):
    """Save ClickUp data atomically."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    
    # Atomic write: write to temp file, then rename
    with tempfile.NamedTemporaryFile(
        mode='w', 
        dir=CACHE_DIR, 
        delete=False,
        suffix='.tmp'
    ) as tmp:
        json.dump(cache_data, tmp)
        tmp_path = tmp.name
    
    # Atomic rename (POSIX guarantee)
    os.replace(tmp_path, CACHE_FILE)

def load_clickup_cache() -> Optional[List[Dict]]:
    """Load cached data if fresh enough."""
    if not CACHE_FILE.exists():
        return None
    
    try:
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        # Corrupted cache
        return None
    
    cached_time = datetime.fromisoformat(cache_data["timestamp"])
    age = datetime.now() - cached_time
    
    if age < timedelta(hours=CACHE_DURATION_HOURS):
        return cache_data["data"]
    
    return None

def refresh_cache_if_stale(fetch_fn) -> List[Dict]:
    """
    Idempotent cache refresh with locking.
    Only one process will fetch; others wait and use the result.
    """
    # Try cache first (no lock needed for read)
    cached = load_clickup_cache()
    if cached is not None:
        return cached
    
    # Cache is stale - try to acquire lock to refresh
    lock_fd = _acquire_lock(LOCK_FILE, timeout=5)
    
    if lock_fd is None:
        # Another process is refreshing, wait for it
        import time
        for _ in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            cached = load_clickup_cache()
            if cached is not None:
                return cached
        
        # Timeout waiting for other process - fetch anyway
        pass
    
    try:
        # Double-check cache under lock (another process might have just updated)
        cached = load_clickup_cache()
        if cached is not None:
            return cached
        
        # Actually fetch fresh data
        data = fetch_fn()
        save_clickup_cache(data)
        return data
    
    finally:
        _release_lock(lock_fd)