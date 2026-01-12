"""
Authentication module for Lelang CLI
Handles browser-based login with captcha and token management
"""
import json
import asyncio
import random
import threading
import httpx
from datetime import datetime
from playwright.async_api import async_playwright
from config import (
    TOKEN_FILE, LOGIN_PAGE_URL, BROWSER_HEADLESS, API_AUTH_BASE_URL,
    REFRESH_TOKEN_ENDPOINT, TOKEN_REFRESH_MIN_INTERVAL, TOKEN_REFRESH_MAX_INTERVAL,
    REQUEST_TIMEOUT
)
from utils import console, print_success, print_error, print_info, print_warning


# Global variable for refresh thread
_refresh_thread = None
_stop_refresh = threading.Event()


def get_stored_token() -> dict | None:
    """Get stored token from file"""
    if not TOKEN_FILE.exists():
        return None
    
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data
    except Exception:
        return None


def save_token(access_token: str, refresh_token: str = None, user_info: dict = None):
    """Save token to file"""
    existing = get_stored_token() or {}
    
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token or existing.get("refresh_token"),
        "saved_at": datetime.now().isoformat(),
        "user_info": user_info or existing.get("user_info")
    }
    
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)


def clear_token():
    """Clear stored token"""
    global _stop_refresh
    _stop_refresh.set()  # Stop refresh thread
    
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        return True
    return False


def is_token_valid() -> bool:
    """Check if stored token exists"""
    token_data = get_stored_token()
    return token_data is not None and "access_token" in token_data


def get_access_token() -> str | None:
    """Get access token string"""
    token_data = get_stored_token()
    if token_data:
        return token_data.get("access_token")
    return None


def get_refresh_token() -> str | None:
    """Get refresh token string"""
    token_data = get_stored_token()
    if token_data:
        return token_data.get("refresh_token")
    return None


def refresh_access_token() -> bool:
    """
    Refresh the access token using refresh token
    Returns True if successful, False otherwise
    
    API Response format:
    {
        "token": "...",
        "refresh_token": "...",
        "notification_token": "..."
    }
    """
    refresh_token = get_refresh_token()
    access_token = get_access_token()
    
    if not refresh_token:
        print_warning("Tidak ada refresh token tersimpan")
        return False
    
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Add Authorization header if we have access token
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            response = client.post(
                REFRESH_TOKEN_ENDPOINT,
                json={"refresh_token": refresh_token},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # API returns: {"token": "...", "refresh_token": "...", "notification_token": "..."}
                new_access_token = data.get("token")
                new_refresh_token = data.get("refresh_token")
                
                if new_access_token:
                    save_token(new_access_token, new_refresh_token)
                    return True
                    
                # Fallback: try data wrapper
                if data.get("data", {}).get("token"):
                    new_access_token = data["data"]["token"]
                    new_refresh_token = data["data"].get("refresh_token")
                    save_token(new_access_token, new_refresh_token)
                    return True
            
            print_error(f"Refresh token failed: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print_error(f"Detail: {error_detail}")
            except:
                pass
            return False
            
    except Exception as e:
        print_error(f"Error saat refresh token: {e}")
        return False


def _token_refresh_worker():
    """Background worker to refresh token periodically"""
    global _stop_refresh
    
    while not _stop_refresh.is_set():
        # Random interval between 30-240 seconds
        interval = random.randint(TOKEN_REFRESH_MIN_INTERVAL, TOKEN_REFRESH_MAX_INTERVAL)
        
        # Wait for interval or until stopped
        if _stop_refresh.wait(interval):
            break
        
        # Refresh token
        if is_token_valid():
            success = refresh_access_token()
            if success:
                console.print(f"[dim]Token refreshed at {datetime.now().strftime('%H:%M:%S')}[/dim]")


def start_token_refresh():
    """Start background token refresh thread"""
    global _refresh_thread, _stop_refresh
    
    if _refresh_thread and _refresh_thread.is_alive():
        return  # Already running
    
    _stop_refresh.clear()
    _refresh_thread = threading.Thread(target=_token_refresh_worker, daemon=True)
    _refresh_thread.start()
    print_info("Background token refresh dimulai")


def stop_token_refresh():
    """Stop background token refresh thread"""
    global _stop_refresh
    _stop_refresh.set()


async def login_with_browser() -> str | None:
    """
    Open browser for login with captcha handling.
    Intercepts API response to extract bearer token.
    Returns the token if successful, None otherwise.
    """
    token = None
    refresh_token = None
    user_info = None
    
    async with async_playwright() as p:
        print_info("Membuka browser untuk login...")
        print_warning("Silakan login dan selesaikan captcha di browser")
        
        browser = await p.chromium.launch(headless=BROWSER_HEADLESS)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Intercept API responses to capture token
        async def handle_response(response):
            nonlocal token, refresh_token, user_info
            
            try:
                # Check for any auth-related responses
                url = response.url.lower()
                
                # Match login API responses
                if ("api-auth" in url or "auth" in url) and ("login" in url or "token" in url):
                    if response.status == 200:
                        try:
                            data = await response.json()
                            
                            # Format 1: {"token": "...", "refresh_token": "..."}
                            if data.get("token") and not token:
                                token = data["token"]
                                refresh_token = data.get("refresh_token")
                                print_success("Token berhasil didapatkan dari response!")
                            
                            # Format 2: {"data": {"access_token": "...", "refresh_token": "..."}}
                            elif data.get("data", {}).get("access_token") and not token:
                                token = data["data"]["access_token"]
                                refresh_token = data["data"].get("refresh_token")
                                user_info = data.get("data", {}).get("user")
                                print_success("Token berhasil didapatkan dari response!")
                            
                            # Format 3: {"access_token": "..."}
                            elif data.get("access_token") and not token:
                                token = data["access_token"]
                                refresh_token = data.get("refresh_token")
                                user_info = data.get("user")
                                print_success("Token berhasil didapatkan dari response!")
                                
                        except Exception as e:
                            pass
                
                # Also check Authorization header in any request
                if response.request.headers.get("authorization"):
                    auth_header = response.request.headers.get("authorization")
                    if auth_header.startswith("Bearer ") and not token:
                        token = auth_header.replace("Bearer ", "")
                        print_success("Token berhasil didapatkan dari header!")
                        
            except Exception:
                pass
        
        page.on("response", handle_response)
        
        # Navigate to login page
        await page.goto(LOGIN_PAGE_URL)
        
        console.print("\n[bold yellow]═══════════════════════════════════════════════════════════[/bold yellow]")
        console.print("[bold]Instruksi:[/bold]")
        console.print("1. Login dengan username dan password Anda")
        console.print("2. Selesaikan captcha yang muncul")
        console.print("3. Setelah login berhasil, browser akan otomatis tertutup")
        console.print("[bold yellow]═══════════════════════════════════════════════════════════[/bold yellow]\n")
        
        # Wait for successful login
        max_wait = 300  # 5 minutes max
        wait_count = 0
        
        try:
            while not token and wait_count < max_wait:
                await asyncio.sleep(1)
                wait_count += 1
                
                # Check if navigated away from login page
                current_url = page.url
                
                if "/login" not in current_url and token is None:
                    print_info(f"Redirected ke: {current_url}")
                    
                    # Try to get token from localStorage
                    try:
                        local_storage_token = await page.evaluate("""
                            () => {
                                // Try various common localStorage keys
                                const keys = ['token', 'access_token', 'accessToken', 'auth_token', 'authToken', 'jwt', 'bearer'];
                                for (const key of keys) {
                                    const value = localStorage.getItem(key);
                                    if (value) return value;
                                }
                                
                                // Try to find in any key containing 'token'
                                for (let i = 0; i < localStorage.length; i++) {
                                    const key = localStorage.key(i);
                                    if (key && key.toLowerCase().includes('token')) {
                                        const value = localStorage.getItem(key);
                                        if (value && !value.startsWith('{')) {
                                            return value;
                                        }
                                        // If JSON, try to parse
                                        try {
                                            const parsed = JSON.parse(value);
                                            if (parsed.access_token) return parsed.access_token;
                                            if (parsed.token) return parsed.token;
                                        } catch(e) {}
                                    }
                                }
                                
                                // Try sessionStorage too
                                for (let i = 0; i < sessionStorage.length; i++) {
                                    const key = sessionStorage.key(i);
                                    if (key && key.toLowerCase().includes('token')) {
                                        const value = sessionStorage.getItem(key);
                                        if (value && !value.startsWith('{')) {
                                            return value;
                                        }
                                    }
                                }
                                
                                return null;
                            }
                        """)
                        
                        if local_storage_token:
                            token = local_storage_token
                            print_success("Token berhasil didapatkan dari localStorage!")
                            break
                            
                    except Exception as e:
                        print_warning(f"Tidak bisa akses localStorage: {e}")
                    
                    # Try cookies
                    try:
                        cookies = await context.cookies()
                        for cookie in cookies:
                            name = cookie.get("name", "").lower()
                            if "token" in name or "auth" in name or "jwt" in name:
                                token = cookie.get("value")
                                print_success(f"Token berhasil didapatkan dari cookie: {cookie.get('name')}")
                                break
                    except Exception:
                        pass
                    
                    if token:
                        break
                    
                    # Wait a bit more after redirect
                    await asyncio.sleep(3)
                    
                    # Final check - if user is on dashboard/home, prompt to check network
                    if not token and ("dashboard" in current_url or "home" in current_url or "beranda" in current_url):
                        print_warning("Login sukses tapi token tidak tertangkap otomatis.")
                        print_info("Mencoba metode alternatif...")
                        
                        # Try to make an authenticated request to /me endpoint
                        await asyncio.sleep(2)
                        break
                        
        except Exception as e:
            print_error(f"Error saat menunggu login: {e}")
        
        await browser.close()
    
    if token:
        save_token(token, refresh_token, user_info)
        print_success(f"Token tersimpan di: {TOKEN_FILE}")
        
        # Auto-refresh immediately to get a new refresh token
        if refresh_token:
            print_info("Auto-refreshing token untuk mendapatkan refresh token baru...")
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                    headers = {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}"
                    }
                    
                    response = client.post(
                        REFRESH_TOKEN_ENDPOINT,
                        json={"refresh_token": refresh_token},
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        new_access_token = data.get("token")
                        new_refresh_token = data.get("refresh_token")
                        
                        if new_access_token:
                            save_token(new_access_token, new_refresh_token, user_info)
                            print_success("Token baru berhasil didapatkan!")
                            print_success("Refresh token baru tersimpan!")
                            token = new_access_token
                        else:
                            print_warning("Auto-refresh berhasil tapi tidak ada token baru.")
                    else:
                        print_warning(f"Auto-refresh gagal: HTTP {response.status_code}")
            except Exception as e:
                print_warning(f"Auto-refresh error: {e}")
        else:
            print_warning("Tidak ada refresh token.")
        
        return token
    else:
        print_error("Gagal mendapatkan token secara otomatis.")
        print_info("Anda bisa memasukkan token secara manual dengan: python main.py set-token <TOKEN>")
        return None


def login_sync() -> str | None:
    """Synchronous wrapper for login_with_browser"""
    return asyncio.run(login_with_browser())


def set_token_manual(token: str, refresh_token: str = None) -> bool:
    """Manually set token"""
    try:
        save_token(token, refresh_token)
        return True
    except Exception:
        return False
