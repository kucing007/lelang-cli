"""
Server Time module for Lelang CLI
Fetches and syncs with lelang.go.id server time
"""
import threading
import httpx
from datetime import datetime, timedelta
from config import REQUEST_TIMEOUT

# Server time API (using response headers from any API)
SERVER_TIME_URL = "https://api.lelang.go.id/api/v1/servertime"
FALLBACK_URL = "https://api.lelang.go.id/health"

# Global variables for server time
_server_time_offset = timedelta(0)  # Offset between local time and server time
_server_time_lock = threading.Lock()
_is_synced = False


def sync_server_time() -> bool:
    """
    Sync with server time by making a request and reading Date header
    Returns True if successful
    """
    global _server_time_offset, _is_synced
    
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            # Try server time endpoint first
            local_before = datetime.now()
            response = client.get(SERVER_TIME_URL)
            local_after = datetime.now()
            
            # Calculate round trip time and estimate
            round_trip = (local_after - local_before).total_seconds()
            local_estimate = local_before + timedelta(seconds=round_trip / 2)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Try to parse server time from response
                    if "data" in data and "time" in data["data"]:
                        server_time_str = data["data"]["time"]
                        server_time = datetime.fromisoformat(server_time_str.replace("Z", "+00:00"))
                        # Convert to local timezone
                        server_time = server_time.replace(tzinfo=None)
                    elif "time" in data:
                        server_time_str = data["time"]
                        server_time = datetime.fromisoformat(server_time_str.replace("Z", "+00:00"))
                        server_time = server_time.replace(tzinfo=None)
                    else:
                        # Use Date header as fallback
                        date_header = response.headers.get("Date")
                        if date_header:
                            server_time = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z")
                            # Adjust for WIB (UTC+7)
                            server_time = server_time + timedelta(hours=7)
                        else:
                            return False
                    
                    with _server_time_lock:
                        _server_time_offset = server_time - local_estimate
                        _is_synced = True
                    
                    return True
                    
                except Exception:
                    pass
            
            # Fallback: use Date header from response
            date_header = response.headers.get("Date")
            if date_header:
                try:
                    server_time = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z")
                    # Adjust for WIB (UTC+7)
                    server_time = server_time + timedelta(hours=7)
                    
                    with _server_time_lock:
                        _server_time_offset = server_time - local_estimate
                        _is_synced = True
                    
                    return True
                except Exception:
                    pass
            
            return False
            
    except Exception:
        return False


def get_server_time() -> datetime:
    """Get current server time based on synced offset"""
    with _server_time_lock:
        return datetime.now() + _server_time_offset


def get_server_time_str() -> str:
    """Get formatted server time string"""
    server_time = get_server_time()
    return server_time.strftime("%d %b %Y, %H:%M:%S WIB")


def is_time_synced() -> bool:
    """Check if time is synced with server"""
    return _is_synced


def get_time_offset_seconds() -> float:
    """Get time offset in seconds"""
    with _server_time_lock:
        return _server_time_offset.total_seconds()


def get_server_time_iso() -> str:
    """Get server time in ISO format for API calls (bidTime)"""
    server_time = get_server_time()
    # Format: 2026-01-11T13:03:12.967Z
    return server_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{server_time.microsecond // 1000:03d}Z"
