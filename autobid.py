"""
AutoBid Bot for Lelang CLI
Ultra-fast burst detection with async concurrent polling
"""
import time
import asyncio
import threading
import httpx
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich import box

from config import BIDDING_HISTORY, BIDDING_SUBMIT, REQUEST_TIMEOUT
from auth import get_stored_token
from server_time import get_server_time_str, get_server_time_iso, get_server_time
from utils import format_currency_full, print_success, print_error, print_warning, print_info

console = Console()


def parse_datetime(dt_str: str) -> datetime | None:
    """Parse ISO datetime string"""
    if not dt_str:
        return None
    try:
        if "T" in dt_str:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None


def format_countdown(seconds: float) -> str:
    """Format seconds to countdown string HH:MM:SS"""
    if seconds <= 0:
        return "[red]SELESAI[/red]"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if seconds < 60:
        return f"[red bold]{secs}s[/red bold]"
    elif seconds < 300:
        return f"[yellow bold]{minutes}m {secs}s[/yellow bold]"
    else:
        return f"[green]{hours}h {minutes}m {secs}s[/green]"


class AutoBidBot:
    """High-speed autobid bot with burst detection and countdown timer"""
    
    def __init__(
        self, 
        lot_lelang_id: str, 
        max_budget: int, 
        kelipatan_bid: int, 
        pin_bidding: str,
        poll_interval_ms: int = 50,
        tgl_selesai: str = "",
        my_user_auction_id: str = ""
    ):
        self.lot_id = lot_lelang_id
        self.max_budget = max_budget
        self.kelipatan_bid = kelipatan_bid
        self.pin = pin_bidding
        self.poll_interval = poll_interval_ms / 1000  # Convert to seconds
        
        # Parse end time for countdown
        self.end_time = parse_datetime(tgl_selesai)
        
        # State
        self.running = False
        self.last_bid_amount = 0
        self.last_bidder_id = ""  # userAuctionId of last bidder
        self.my_user_auction_id = my_user_auction_id  # My own userAuctionId
        self.my_last_bid = 0
        self.total_bids_submitted = 0
        self.total_requests = 0
        self.avg_response_time_ms = 0
        self.last_response_time_ms = 0
        self.is_my_bid = False  # Track if last bid is mine
        
        # Stats
        self.start_time = None
        self.errors = []
        
        # HTTP client with connection pooling (reuse connections for speed)
        self._client = None
        self._headers = None
    
    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client with connection pooling and speed optimizations"""
        if self._client is None:
            # Optimized settings for maximum speed
            self._client = httpx.Client(
                timeout=httpx.Timeout(5.0, connect=2.0, read=3.0),  # Shorter timeouts
                limits=httpx.Limits(
                    max_keepalive_connections=20,  # More keep-alive connections
                    max_connections=50,  # More concurrent connections
                    keepalive_expiry=30  # Keep connections alive longer
                )
            )
        return self._client
    
    def _get_headers(self) -> dict:
        """Get cached auth headers"""
        if self._headers is None:
            token_data = get_stored_token()
            if not token_data or "access_token" not in token_data:
                raise ValueError("Token tidak ditemukan")
            self._headers = {
                "Authorization": f"Bearer {token_data['access_token']}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        return self._headers
    
    def get_remaining_seconds(self) -> float:
        """Get remaining seconds until auction ends"""
        if not self.end_time:
            return 9999999  # No end time, assume infinite
        
        server_now = get_server_time()
        remaining = (self.end_time - server_now).total_seconds()
        return max(0, remaining)
    
    def get_latest_bid_fast(self) -> tuple[int, str, int, float]:
        """
        Get latest bid amount with minimal latency
        Returns: (bid_amount, user_auction_id, my_last_bid, response_time_ms)
        """
        url = f"{BIDDING_HISTORY}/{self.lot_id}/riwayat"
        
        start = time.perf_counter()
        try:
            response = self._get_client().get(url, headers=self._get_headers())
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", [])
                if items:
                    # Get latest bid (first item) - use userAuctionId for identification
                    bid_amount = items[0].get("bidAmount", 0)
                    user_auction_id = items[0].get("userAuctionId", "")
                    
                    # Search for my own last bid in history using userAuctionId
                    my_bid = 0
                    if self.my_user_auction_id:
                        for item in items:
                            if item.get("userAuctionId") == self.my_user_auction_id:
                                my_bid = item.get("bidAmount", 0)
                                break  # First match is the most recent
                    
                    return bid_amount, user_auction_id, my_bid, elapsed_ms
            return 0, "", 0, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.errors.append(str(e))
            return 0, "", 0, elapsed_ms
    
    def get_latest_bid_concurrent(self, num_requests: int = 3) -> tuple[int, str, int, float]:
        """
        Get latest bid using concurrent requests - returns fastest response
        Sends multiple parallel requests and uses the first successful one
        Returns: (bid_amount, user_auction_id, my_last_bid, response_time_ms)
        """
        url = f"{BIDDING_HISTORY}/{self.lot_id}/riwayat"
        headers = self._get_headers()
        
        def fetch_bid():
            start = time.perf_counter()
            try:
                response = self._get_client().get(url, headers=headers)
                elapsed = (time.perf_counter() - start) * 1000
                if response.status_code == 200:
                    return response.json(), elapsed
                return None, elapsed
            except:
                return None, (time.perf_counter() - start) * 1000
        
        # Execute concurrent requests
        start_total = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(fetch_bid) for _ in range(num_requests)]
            
            # Get first successful response
            for future in as_completed(futures):
                data, elapsed = future.result()
                if data:
                    items = data.get("data", [])
                    if items:
                        bid_amount = items[0].get("bidAmount", 0)
                        user_auction_id = items[0].get("userAuctionId", "")
                        
                        my_bid = 0
                        if self.my_user_auction_id:
                            for item in items:
                                if item.get("userAuctionId") == self.my_user_auction_id:
                                    my_bid = item.get("bidAmount", 0)
                                    break
                        
                        return bid_amount, user_auction_id, my_bid, elapsed
        
        return 0, "", 0, (time.perf_counter() - start_total) * 1000
    
    def submit_bid_fast(self, bid_amount: int) -> tuple[bool, str, float]:
        """
        Submit bid with minimal latency
        Returns: (success, message, response_time_ms)
        """
        bid_time = get_server_time_iso()
        payload = {
            "auctionId": self.lot_id,
            "bidAmount": bid_amount,
            "passkey": self.pin,
            "bidTime": bid_time
        }
        
        start = time.perf_counter()
        try:
            response = self._get_client().post(
                BIDDING_SUBMIT, 
                headers=self._get_headers(), 
                json=payload
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    return True, "Success", elapsed_ms
                return False, data.get("message", "Unknown error"), elapsed_ms
            return False, f"HTTP {response.status_code}", elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return False, str(e), elapsed_ms
    
    def _create_status_panel(self) -> Panel:
        """Create rich status panel for live display with countdown"""
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("Label", style="cyan", width=22)
        table.add_column("Value", style="white", width=35)
        
        status = "[green]RUNNING[/green]" if self.running else "[red]STOPPED[/red]"
        table.add_row("Status", status)
        table.add_row("Server Time", get_server_time_str())
        
        # Countdown timer
        remaining = self.get_remaining_seconds()
        table.add_row("⏱️  Sisa Waktu", format_countdown(remaining))
        
        table.add_row("", "")
        table.add_row("Budget Maksimal", f"[yellow]{format_currency_full(self.max_budget)}[/yellow]")
        table.add_row("Kelipatan Bid", format_currency_full(self.kelipatan_bid))
        table.add_row("", "")
        
        # Show last bid with indicator if it's mine
        if self.is_my_bid:
            table.add_row("Penawaran Terakhir", f"[cyan]{format_currency_full(self.last_bid_amount)}[/cyan] [green](SAYA)[/green]")
        else:
            table.add_row("Penawaran Terakhir", f"[green]{format_currency_full(self.last_bid_amount)}[/green] [yellow](Lawan)[/yellow]")
        table.add_row("Bid Saya Terakhir", f"[cyan]{format_currency_full(self.my_last_bid)}[/cyan]")
        table.add_row("", "")
        table.add_row("Total Bid Submitted", str(self.total_bids_submitted))
        table.add_row("Total API Requests", str(self.total_requests))
        table.add_row("Last Response Time", f"[bold]{self.last_response_time_ms:.0f}ms[/bold]")
        table.add_row("Avg Response Time", f"{self.avg_response_time_ms:.0f}ms")
        
        if self.errors:
            table.add_row("", "")
            table.add_row("[red]Last Error[/red]", f"[red]{self.errors[-1][:30]}[/red]")
        
        return Panel(
            table, 
            title="[bold cyan]🤖 BOT AUTOBID[/bold cyan]", 
            subtitle="[dim]Tekan Ctrl+C untuk berhenti[/dim]",
            border_style="cyan"
        )
    
    def run(self):
        """Run the autobid bot with live status display"""
        self.running = True
        self.start_time = time.time()
        total_response_time = 0
        
        console.print("\n[bold green]🚀 Bot Autobid dimulai![/bold green]")
        console.print(f"[dim]Polling interval: {self.poll_interval * 1000:.0f}ms[/dim]")
        
        # Fetch initial bid data before starting
        console.print("[dim]Mengambil data penawaran terakhir...[/dim]")
        console.print(f"[dim]My PesertaId: {self.my_user_auction_id}[/dim]")  # DEBUG
        initial_bid, initial_bidder, my_bid_from_history, initial_time = self.get_latest_bid_fast()
        self.total_requests += 1
        
        # DEBUG: Show bidder ID from history
        console.print(f"[dim]Last bidder ID: {initial_bidder}[/dim]")
        console.print(f"[dim]Match: {initial_bidder == self.my_user_auction_id}[/dim]")
        
        if initial_bid > 0:
            self.last_bid_amount = initial_bid
            self.last_bidder_id = initial_bidder
            self.is_my_bid = (initial_bidder == self.my_user_auction_id) if self.my_user_auction_id else False
            # Set my_last_bid from history search
            if my_bid_from_history > 0:
                self.my_last_bid = my_bid_from_history
            console.print(f"[green]✓ Penawaran terakhir: {format_currency_full(initial_bid)}[/green]")
            if my_bid_from_history > 0:
                console.print(f"[cyan]✓ Bid saya terakhir: {format_currency_full(my_bid_from_history)}[/cyan]")
        else:
            console.print("[yellow]! Belum ada penawaran atau gagal mengambil data[/yellow]")
            if self.errors:
                console.print(f"[red]  Error: {self.errors[-1][:50]}[/red]")
        
        console.print("")  # Empty line before live display
        
        try:
            with Live(self._create_status_panel(), console=console, refresh_per_second=10) as live:
                while self.running:
                    # Check if auction has ended
                    remaining = self.get_remaining_seconds()
                    if remaining <= 0:
                        console.print("\n[yellow]⏱️ Lelang telah berakhir![/yellow]")
                        self.running = False
                        break
                    
                    # Concurrent poll for latest bid (3 parallel requests, use fastest)
                    current_bid, bidder_id, my_bid_now, response_time = self.get_latest_bid_concurrent(3)
                    self.total_requests += 3  # Count all 3 concurrent requests
                    self.last_response_time_ms = response_time
                    total_response_time += response_time
                    self.avg_response_time_ms = total_response_time / (self.total_requests // 3)
                    
                    # Update my_last_bid from history
                    if my_bid_now > 0:
                        self.my_last_bid = my_bid_now
                    if current_bid > 0:
                        self.last_bid_amount = current_bid
                        self.last_bidder_id = bidder_id
                        
                        # Check if this bid is mine
                        self.is_my_bid = (bidder_id == self.my_user_auction_id) if self.my_user_auction_id else False
                        
                        # Only bid if last bidder is NOT me
                        if not self.is_my_bid and current_bid >= self.my_last_bid:
                            # Calculate next bid
                            next_bid = current_bid + self.kelipatan_bid
                            
                            # Check budget
                            if next_bid <= self.max_budget:
                                # Submit bid immediately!
                                success, msg, submit_time = self.submit_bid_fast(next_bid)
                                self.total_requests += 1
                                
                                if success:
                                    self.my_last_bid = next_bid
                                    self.total_bids_submitted += 1
                                    self.last_response_time_ms = submit_time
                                else:
                                    self.errors.append(msg)
                            else:
                                # Budget exceeded
                                console.print(f"\n[yellow]⚠️ Budget exceeded! Next bid {format_currency_full(next_bid)} > max {format_currency_full(self.max_budget)}[/yellow]")
                                self.running = False
                                break
                    
                    # Update display
                    live.update(self._create_status_panel())
                    
                    # Wait for next poll
                    time.sleep(self.poll_interval)
                    
        except KeyboardInterrupt:
            self.running = False
            console.print("\n[yellow]Bot dihentikan oleh user.[/yellow]")
        finally:
            self._cleanup()
        
        # Print summary
        self._print_summary()
    
    def _cleanup(self):
        """Cleanup resources"""
        if self._client:
            self._client.close()
            self._client = None
    
    def _print_summary(self):
        """Print bot session summary"""
        duration = time.time() - self.start_time if self.start_time else 0
        
        console.print("\n[bold cyan]═══════════════ SUMMARY ═══════════════[/bold cyan]")
        console.print(f"Durasi: {duration:.1f} detik")
        console.print(f"Total Requests: {self.total_requests}")
        console.print(f"Total Bids: {self.total_bids_submitted}")
        console.print(f"Avg Response: {self.avg_response_time_ms:.0f}ms")
        console.print(f"Bid Terakhir Saya: {format_currency_full(self.my_last_bid)}")
        if self.errors:
            console.print(f"[red]Errors: {len(self.errors)}[/red]")


def run_autobid_bot(
    lot_lelang_id: str,
    max_budget: int,
    kelipatan_bid: int,
    pin_bidding: str,
    poll_interval_ms: int = 50,
    tgl_selesai: str = "",
    my_user_auction_id: str = ""
):
    """
    Run autobid bot with given parameters
    
    Args:
        lot_lelang_id: Auction lot ID
        max_budget: Maximum budget for bidding
        kelipatan_bid: Bid increment amount
        pin_bidding: Bidding PIN
        poll_interval_ms: Polling interval in milliseconds (default 50ms)
        tgl_selesai: Auction end time (ISO format)
        my_user_auction_id: User's own auction ID to avoid self-bidding
    """
    bot = AutoBidBot(
        lot_lelang_id=lot_lelang_id,
        max_budget=max_budget,
        kelipatan_bid=kelipatan_bid,
        pin_bidding=pin_bidding,
        poll_interval_ms=poll_interval_ms,
        tgl_selesai=tgl_selesai,
        my_user_auction_id=my_user_auction_id
    )
    bot.run()
