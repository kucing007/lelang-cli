#!/usr/bin/env python3
"""
Lelang CLI - Command Line Interface untuk lelang.go.id
"""
import click
import time as time_module
import os
from rich.console import Console
from rich.panel import Panel
from rich.live import Live

from auth import (
    login_sync, clear_token, is_token_valid, get_stored_token, 
    set_token_manual, start_token_refresh, stop_token_refresh,
    refresh_access_token
)
from api import api_client
from utils import (
    print_success, 
    print_error, 
    print_info, 
    print_warning, 
    print_user_profile,
    print_lelang_list,
    print_lelang_detail,
    print_kpknl_list,
    print_katalog_list,
    print_lot_info_public,
    print_kategori_list,
    print_provinsi_list,
    print_kota_list,
    format_date,
    format_currency,
    format_currency_full,
    export_katalog_to_csv,
    print_bid_history,
    print_bidding_info
)
from server_time import sync_server_time, get_server_time_str, is_time_synced

console = Console()


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Print application banner with server time"""
    if not is_time_synced():
        sync_server_time()
    
    time_display = get_server_time_str()
    
    banner = f"""
[bold cyan]╔═══════════════════════════════════════════════════════════╗
║           🏛️  LELANG CLI - lelang.go.id  🏛️              ║
║                  Command Line Interface v3.1              ║
╠═══════════════════════════════════════════════════════════╣
║  🕐 Server Time: {time_display:<39}║
╚═══════════════════════════════════════════════════════════╝[/bold cyan]
"""
    console.print(banner)


def _wait_for_enter():
    """Wait for user to press Enter"""
    click.prompt("\nTekan Enter untuk lanjut", default="", show_default=False)


@click.group()
@click.version_option(version="3.1.0", prog_name="Lelang CLI")
def cli():
    """Lelang CLI - Command Line Interface untuk lelang.go.id"""
    sync_server_time()


@cli.command()
def login():
    """Login ke lelang.go.id dengan browser"""
    print_banner()
    
    if is_token_valid():
        print_warning("Anda sudah login.")
        if not click.confirm("Login ulang?"):
            return
        clear_token()
    
    print_info("Memulai login...")
    token = login_sync()
    
    if token:
        print_success("Login berhasil!")
        profile = api_client.get_user_profile()
        if profile and profile.get("code") == 200:
            print_user_profile(profile)
    else:
        print_error("Login gagal.")


@cli.command()
def me():
    """Tampilkan profil pengguna"""
    print_banner()
    
    if not is_token_valid():
        print_error("Belum login.")
        return
    
    profile = api_client.get_user_profile()
    if profile and profile.get("code") == 200:
        print_user_profile(profile)


@cli.command()
def status():
    """Cek status login"""
    print_banner()
    
    token_data = get_stored_token()
    if not token_data:
        console.print(Panel("[bold red]Belum Login[/bold red]", title="Status", border_style="red"))
        return
    
    profile = api_client.get_user_profile()
    if profile and profile.get("code") == 200:
        user = profile.get("data", {})
        console.print(Panel(
            f"[bold green]✓ Login Aktif[/bold green]\n\n"
            f"Nama: {user.get('nama', '-')}\n"
            f"Email: {user.get('email', '-')}",
            title="Status",
            border_style="green"
        ))


@cli.command()
def logout():
    """Logout"""
    if click.confirm("Logout?"):
        stop_token_refresh()
        clear_token()
        print_success("Berhasil logout.")


@cli.command("set-token")
@click.argument("token")
@click.option("--refresh", "-r", default=None, help="Refresh token (optional)")
def set_token(token: str, refresh: str = None):
    """Set token manual dari browser.
    
    \b
    Cara mendapatkan token:
    1. Login ke https://lelang.go.id
    2. Buka DevTools (F12) → Application → Local Storage
    3. Copy value dari key 'token' atau 'accessToken'
    
    \b
    Contoh penggunaan:
      python main.py set-token "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
    """
    if set_token_manual(token, refresh):
        print_success("Token disimpan!")



@cli.command("refresh-token")
def refresh_token_cmd():
    """Refresh access token"""
    if refresh_access_token():
        print_success("Token di-refresh!")
    else:
        print_error("Gagal refresh.")


@cli.command("server-time")
def show_server_time():
    """Tampilkan server time realtime"""
    if not is_time_synced():
        sync_server_time()
    
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                live.update(Panel(f"[bold green]{get_server_time_str()}[/bold green]", title="🕐 Server Time"))
                time_module.sleep(0.1)
    except KeyboardInterrupt:
        pass


@cli.command("browse")
def browse_cmd():
    """Browse katalog lelang"""
    _browse_interactive()


@cli.command()
def interactive():
    """Mode interaktif"""
    sync_server_time()
    
    if is_token_valid():
        start_token_refresh()
    
    try:
        while True:
            clear_screen()
            print_banner()
            
            console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
            console.print("[bold cyan]              MENU UTAMA               [/bold cyan]")
            console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
            console.print("1. 🔑 Login")
            console.print("2. 👤 Lihat Profil")
            console.print("3. 📋 Lelang Saya")
            console.print("4. 🔍 [bold]Browse Katalog Lelang[/bold]")
            console.print("5. 🔄 Refresh Token")
            console.print("6. 📊 Cek Status")
            console.print("7. 🕐 Server Time")
            console.print("8. 🚪 Logout")
            console.print("0. ❌ Keluar")
            
            choice = click.prompt("\nPilih", type=int, default=0)
            
            if choice == 1:
                ctx = click.Context(login)
                ctx.invoke(login)
                if is_token_valid():
                    start_token_refresh()
                _wait_for_enter()
            elif choice == 2:
                ctx = click.Context(me)
                ctx.invoke(me)
                _wait_for_enter()
            elif choice == 3:
                _lelang_saya_interactive()
            elif choice == 4:
                _browse_interactive()
            elif choice == 5:
                ctx = click.Context(refresh_token_cmd)
                ctx.invoke(refresh_token_cmd)
                _wait_for_enter()
            elif choice == 6:
                ctx = click.Context(status)
                ctx.invoke(status)
                _wait_for_enter()
            elif choice == 7:
                ctx = click.Context(show_server_time)
                ctx.invoke(show_server_time)
            elif choice == 8:
                ctx = click.Context(logout)
                ctx.invoke(logout)
                _wait_for_enter()
            elif choice == 0:
                print_info("Terima kasih!")
                break
                
    finally:
        stop_token_refresh()


def _lelang_saya_interactive():
    """Interactive Lelang Saya"""
    if not is_token_valid():
        print_error("Belum login.")
        _wait_for_enter()
        return
    
    page = 1
    limit = 10
    
    while True:
        clear_screen()
        console.print(f"\n[bold cyan]🕐 {get_server_time_str()}[/bold cyan]")
        console.print("[bold cyan]═══════════════ LELANG SAYA ═══════════════[/bold cyan]")
        
        # Ask for limit
        limit = click.prompt("Tampilkan berapa data", type=int, default=limit)
        
        print_info(f"Mengambil data (hal {page})...")
        data = api_client.get_lelang_saya(page=page, limit=limit)
        
        if not data or data.get("code") != 200:
            print_error("Gagal mengambil data.")
            _wait_for_enter()
            break
        
        items = print_lelang_list(data)
        total_pages = data.get("totalPages", 1)
        
        if not items:
            _wait_for_enter()
            break
        
        console.print("\n[dim]1-N: Detail | n: Next | p: Prev | 0: Kembali[/dim]")
        choice = click.prompt("Pilih", type=str, default="0")
        
        if choice == "0":
            break
        elif choice.lower() == "n":
            if page < total_pages:
                page += 1
        elif choice.lower() == "p":
            if page > 1:
                page -= 1
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(items):
                    lot_id = items[idx - 1].get("lot_lelang_id")
                    status_peserta = items[idx - 1].get("status_peserta", "")
                    
                    if lot_id:
                        print_info("Mengambil detail...")
                        detail = api_client.get_lelang_detail(lot_id)
                        if detail and detail.get("code") == 200:
                            print_lelang_detail(detail.get("data", detail))
                            
                            # Check if status is "Peserta Bidding" - show bidding options
                            if "BIDDING" in status_peserta.upper() or "PESERTA" in status_peserta.upper():
                                console.print("\n[bold cyan]═══════════════ OPSI BIDDING ═══════════════[/bold cyan]")
                                console.print("1. 🚀 Mulai Lelang / Masuk ke Menu Bidding")
                                console.print("0. ⬅️  Kembali")
                                
                                bid_choice = click.prompt("\nPilih", type=int, default=0)
                                if bid_choice == 1:
                                    _bidding_menu(lot_id, detail.get("data", detail))
                            else:
                                _wait_for_enter()
                        else:
                            _wait_for_enter()
            except ValueError:
                pass


def _bidding_menu(lot_lelang_id: str, detail_data: dict):
    """Interactive bidding menu for auction participation"""
    # Extract lot info for kelipatan bid
    lot_lelang = detail_data.get("lotLelang", {})
    kelipatan_bid = int(float(lot_lelang.get("kelipatanBid", 50000) or 50000))
    nilai_limit = int(float(lot_lelang.get("nilaiLimit", 0) or 0))
    tgl_selesai = lot_lelang.get("tglSelesaiLelang", "")
    
    # Get PIN and status
    print_info("Mengambil info bidding...")
    status_data = api_client.get_auction_status_with_pin(lot_lelang_id)
    
    pin_bidding = ""
    my_peserta_id = ""  # pesertaId from status API, matches userAuctionId in bid history
    if status_data and status_data.get("code") == 200:
        data = status_data.get("data", {})
        # PIN is in data.peserta.pinBidding, pesertaId is in data.peserta.pesertaId
        peserta = data.get("peserta", {})
        pin_bidding = peserta.get("pinBidding", "")
        my_peserta_id = peserta.get("pesertaId", "")
    
    while True:
        clear_screen()
        console.print(f"\n[bold cyan]🕐 {get_server_time_str()}[/bold cyan]")
        console.print("[bold cyan]═══════════════ MENU BIDDING ═══════════════[/bold cyan]")
        
        # Show basic info
        console.print(f"\n[bold]Lot:[/bold] {lot_lelang.get('namaLotLelang', '-')[:50]}")
        console.print(f"[bold]Nilai Limit:[/bold] {format_currency_full(nilai_limit)}")
        console.print(f"[bold]Kelipatan Bid:[/bold] {format_currency_full(kelipatan_bid)}")
        if pin_bidding:
            console.print(f"[bold]PIN Bidding:[/bold] [yellow]{pin_bidding}[/yellow]")
        
        console.print("\n[bold cyan]═══════════════ PILIHAN ═══════════════[/bold cyan]")
        console.print("1. 🚀 Mulai Sesi Lelang")
        console.print("2. 📋 Lihat Riwayat Penawaran")
        console.print("3. 💰 Ajukan Penawaran")
        console.print("4. 🔄 Refresh Info Bidding")
        console.print("5. 🤖 [bold yellow]Bot Autobid[/bold yellow]")
        console.print("0. ⬅️  Kembali")
        
        choice = click.prompt("\nPilih", type=int, default=0)
        
        if choice == 0:
            break
        elif choice == 1:
            # Mulai Sesi Lelang
            print_info("Memulai sesi lelang...")
            result = api_client.start_auction_session(lot_lelang_id)
            if result:
                if result.get("code") == 200:
                    print_success("Sesi lelang berhasil dimulai!")
                else:
                    print_warning(f"Response: {result.get('message', result)}")
            else:
                print_error("Gagal memulai sesi lelang.")
            _wait_for_enter()
            
        elif choice == 2:
            # Lihat Riwayat Penawaran
            print_info("Mengambil riwayat penawaran...")
            history = api_client.get_bid_history(lot_lelang_id)
            if history and history.get("code") == 200:
                print_bid_history(history)
            else:
                print_warning("Tidak ada riwayat atau gagal mengambil data.")
            _wait_for_enter()
            
        elif choice == 3:
            # Ajukan Penawaran
            _submit_bid_interactive(lot_lelang_id, kelipatan_bid, pin_bidding)
            
        elif choice == 4:
            # Refresh Info Bidding
            print_info("Mengambil info bidding...")
            status_data = api_client.get_auction_status_with_pin(lot_lelang_id)
            if status_data and status_data.get("code") == 200:
                result = print_bidding_info(status_data)
                if result:
                    pin_bidding = result[0]
                    if result[1]:
                        kelipatan_bid = result[1]
            _wait_for_enter()
        
        elif choice == 5:
            # Bot Autobid
            _autobid_interactive(lot_lelang_id, kelipatan_bid, pin_bidding, nilai_limit, tgl_selesai, my_peserta_id)


def _submit_bid_interactive(lot_lelang_id: str, kelipatan_bid: int, pin_bidding: str):
    """Interactive bid submission"""
    from server_time import get_server_time_iso
    
    clear_screen()
    console.print(f"\n[bold cyan]🕐 {get_server_time_str()}[/bold cyan]")
    console.print("[bold cyan]═══════════════ AJUKAN PENAWARAN ═══════════════[/bold cyan]")
    
    # Get latest bid history to calculate next bid
    print_info("Mengambil riwayat penawaran terakhir...")
    history = api_client.get_bid_history(lot_lelang_id)
    
    last_bid = 0
    if history and history.get("code") == 200:
        items = history.get("data", [])
        if items:
            last_bid = items[0].get("bidAmount", 0)
            console.print(f"\n[bold]Penawaran Terakhir:[/bold] {format_currency_full(last_bid)}")
    
    console.print(f"[bold]Kelipatan Bid:[/bold] {format_currency_full(kelipatan_bid)}")
    
    # Ask for multiplier
    console.print(f"\n[dim]Jumlah kelipatan: berapa kali kelipatan bid ({format_currency_full(kelipatan_bid)})[/dim]")
    multiplier = click.prompt("Jumlah kelipatan", type=int, default=1)
    
    # Calculate bid amount
    bid_amount = last_bid + (kelipatan_bid * multiplier)
    console.print(f"\n[bold]Nilai Penawaran:[/bold] [green]{format_currency_full(bid_amount)}[/green]")
    console.print(f"[dim]= {format_currency_full(last_bid)} + ({kelipatan_bid} x {multiplier})[/dim]")
    
    # Get or ask for PIN
    if not pin_bidding:
        pin_bidding = click.prompt("Masukkan PIN Bidding", type=str)
    else:
        console.print(f"[bold]PIN:[/bold] {pin_bidding}")
    
    if not click.confirm("\nKonfirmasi pengajuan penawaran?"):
        print_info("Dibatalkan.")
        _wait_for_enter()
        return
    
    # Get server time for bidTime
    bid_time = get_server_time_iso()
    
    print_info(f"Mengajukan penawaran {format_currency_full(bid_amount)}...")
    result = api_client.submit_bid(lot_lelang_id, bid_amount, pin_bidding, bid_time)
    
    if result:
        if result.get("code") == 200:
            print_success(f"Penawaran {format_currency_full(bid_amount)} berhasil diajukan!")
        else:
            print_warning(f"Response: {result.get('message', result)}")
    else:
        print_error("Gagal mengajukan penawaran.")
    
    _wait_for_enter()


def _autobid_interactive(lot_lelang_id: str, kelipatan_bid: int, pin_bidding: str, nilai_limit: int, tgl_selesai: str = "", my_user_auction_id: str = ""):
    """Interactive autobid bot setup"""
    from autobid import run_autobid_bot
    
    clear_screen()
    console.print(f"\n[bold cyan]🕐 {get_server_time_str()}[/bold cyan]")
    console.print("[bold cyan]═══════════════ BOT AUTOBID ═══════════════[/bold cyan]")
    
    console.print(f"\n[bold]Kelipatan Bid:[/bold] {format_currency_full(kelipatan_bid)}")
    console.print(f"[bold]Nilai Limit:[/bold] {format_currency_full(nilai_limit)}")
    if tgl_selesai:
        console.print(f"[bold]Selesai Lelang:[/bold] [yellow]{format_date(tgl_selesai)}[/yellow]")
    
    if not pin_bidding:
        print_error("PIN Bidding tidak ditemukan!")
        pin_bidding = click.prompt("Masukkan PIN Bidding", type=str)
    else:
        console.print(f"[bold]PIN Bidding:[/bold] [yellow]{pin_bidding}[/yellow]")
    
    console.print("\n[bold yellow]⚠️  PERHATIAN:[/bold yellow]")
    console.print("[dim]Bot akan otomatis mengajukan penawaran setiap ada bid baru[/dim]")
    console.print("[dim]Tekan Ctrl+C untuk menghentikan bot kapan saja[/dim]")
    
    # Get max budget
    default_budget = nilai_limit + (kelipatan_bid * 10)
    console.print(f"\n[dim]Masukkan budget maksimal (minimal {format_currency_full(nilai_limit + kelipatan_bid)})[/dim]")
    max_budget = click.prompt("Budget Maksimal (Rp)", type=int, default=default_budget)
    
    if max_budget < nilai_limit:
        print_error(f"Budget harus lebih dari nilai limit ({format_currency_full(nilai_limit)})")
        _wait_for_enter()
        return
    
    # Get polling interval - allow very fast polling for burst mode
    console.print(f"\n[dim]Interval polling (10-500ms, default 20ms untuk burst mode)[/dim]")
    poll_interval = click.prompt("Interval (ms)", type=int, default=20)
    poll_interval = max(10, min(500, poll_interval))  # Clamp between 10-500ms
    
    # Get sniper mode - start bidding X seconds before auction ends
    console.print(f"\n[bold yellow]🎯 SNIPER MODE[/bold yellow]")
    console.print("[dim]Bot akan standby dan mulai bid di detik-detik terakhir[/dim]")
    console.print("[dim]Masukkan 0 untuk bid langsung (tanpa sniper mode)[/dim]")
    sniper_seconds = click.prompt("Mulai bid (detik sebelum selesai)", type=int, default=10)
    sniper_seconds = max(0, min(300, sniper_seconds))  # Clamp between 0-300 seconds
    
    console.print(f"\n[bold]Konfigurasi Bot:[/bold]")
    console.print(f"  Budget Maksimal: [green]{format_currency_full(max_budget)}[/green]")
    console.print(f"  Kelipatan Bid: {format_currency_full(kelipatan_bid)}")
    console.print(f"  Polling Interval: {poll_interval}ms")
    if sniper_seconds > 0:
        console.print(f"  [yellow]🎯 Sniper Mode: Mulai bid {sniper_seconds} detik sebelum selesai[/yellow]")
    else:
        console.print(f"  Sniper Mode: [dim]Disabled (bid langsung)[/dim]")
    
    if not click.confirm("\n[bold]Mulai Bot Autobid?[/bold]"):
        print_info("Dibatalkan.")
        _wait_for_enter()
        return
    
    # Run the bot!
    run_autobid_bot(
        lot_lelang_id=lot_lelang_id,
        max_budget=max_budget,
        kelipatan_bid=kelipatan_bid,
        pin_bidding=pin_bidding,
        poll_interval_ms=poll_interval,
        tgl_selesai=tgl_selesai,
        my_user_auction_id=my_user_auction_id,
        sniper_seconds=sniper_seconds
    )
    
    _wait_for_enter()


def _browse_interactive():
    """Interactive browse menu"""
    while True:
        clear_screen()
        console.print(f"\n[bold cyan]🕐 {get_server_time_str()}[/bold cyan]")
        console.print("[bold cyan]═══════════ BROWSE KATALOG LELANG ═══════════[/bold cyan]")
        console.print("1. 🏛️  Berdasarkan KPKNL")
        console.print("2. 📋 Katalog Umum (Filter Lengkap)")
        console.print("0. ⬅️  Kembali")
        
        choice = click.prompt("\nPilih", type=int, default=0)
        
        if choice == 1:
            _browse_kpknl()
        elif choice == 2:
            _browse_katalog_umum()
        elif choice == 0:
            break


def _browse_kpknl():
    """Browse by KPKNL"""
    print_info("Mengambil daftar KPKNL...")
    data = api_client.get_kpknl_list()
    
    if not data or data.get("code") != 200:
        print_error("Gagal mengambil data.")
        _wait_for_enter()
        return
    
    items = print_kpknl_list(data)
    
    if not items:
        _wait_for_enter()
        return
    
    console.print("\n[dim]Masukkan nomor KPKNL atau 0 untuk kembali[/dim]")
    choice = click.prompt("Pilih KPKNL", type=int, default=0)
    
    if 1 <= choice <= len(items):
        selected = items[choice - 1]
        _browse_katalog_kpknl(selected.get("id"), selected.get("nama", "KPKNL"))


def _browse_katalog_kpknl(kpknl_id: str, kpknl_nama: str):
    """Browse katalog for specific KPKNL"""
    page = 1
    limit = 10
    filters = {}
    
    while True:
        clear_screen()
        console.print(f"\n[bold cyan]🕐 {get_server_time_str()}[/bold cyan]")
        console.print(f"[bold cyan]═══════════ {kpknl_nama.upper()[:35]} ═══════════[/bold cyan]")
        
        # Show active filters
        if filters:
            console.print("[dim]Filter aktif:[/dim]")
            if filters.get("limit_bawah") or filters.get("limit_atas"):
                console.print(f"  💰 Harga: {format_currency(filters.get('limit_bawah', 0))} - {format_currency(filters.get('limit_atas', 999999999999))}")
        
        # Ask for limit
        limit = click.prompt("Tampilkan berapa data", type=int, default=limit)
        
        print_info(f"Mengambil katalog (hal {page})...")
        
        data = api_client.get_katalog_kpknl(
            kpknl_id=kpknl_id,
            page=page,
            limit=limit,
            **filters
        )
        
        if not data or data.get("code") != 200:
            print_error("Gagal mengambil data.")
            _wait_for_enter()
            break
        
        items = print_katalog_list(data)
        total_page = data.get("totalPage", 1)
        
        if not items:
            _wait_for_enter()
            break
        
        console.print("\n[bold]Pilihan:[/bold]")
        console.print("[dim]1-N: Detail | n/p: Halaman | f: Filter | c: Clear | e: Export CSV | 0: Kembali[/dim]")
        
        choice = click.prompt("Pilih", type=str, default="0")
        
        if choice == "0":
            break
        elif choice.lower() == "n":
            if page < total_page:
                page += 1
        elif choice.lower() == "p":
            if page > 1:
                page -= 1
        elif choice.lower() == "f":
            filters = _set_basic_filters()
            page = 1
        elif choice.lower() == "c":
            filters = {}
            page = 1
        elif choice.lower() == "e":
            export_katalog_to_csv(items)
            _wait_for_enter()
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(items):
                    lot_id = items[idx - 1].get("lotLelangId")
                    if lot_id:
                        _view_lot_detail(lot_id)
            except ValueError:
                pass


def _browse_katalog_umum():
    """Browse general catalog with full filters"""
    page = 1
    limit = 10
    filters = {}
    
    while True:
        clear_screen()
        console.print(f"\n[bold cyan]🕐 {get_server_time_str()}[/bold cyan]")
        console.print("[bold cyan]═══════════ KATALOG UMUM ═══════════[/bold cyan]")
        
        # Show active filters
        if filters:
            console.print("[dim]Filter aktif:[/dim]")
            if filters.get("limit_bawah") or filters.get("limit_atas"):
                console.print(f"  💰 Harga: {format_currency(filters.get('limit_bawah', 0))} - {format_currency(filters.get('limit_atas', 999999999999))}")
            if filters.get("kategori"):
                console.print(f"  📁 Kategori: {', '.join(filters['kategori'])}")
            if filters.get("lokasi"):
                console.print(f"  📍 Lokasi: {len(filters['lokasi'])} kota dipilih")
        
        # Ask for limit
        limit = click.prompt("Tampilkan berapa data", type=int, default=limit)
        
        print_info(f"Mengambil katalog (hal {page})...")
        
        data = api_client.get_katalog_umum(
            page=page,
            limit=limit,
            **filters
        )
        
        if not data or data.get("code") != 200:
            print_error("Gagal mengambil data.")
            _wait_for_enter()
            break
        
        items = print_katalog_list(data)
        total_page = data.get("totalPage", 1)
        
        if not items:
            _wait_for_enter()
            break
        
        console.print("\n[bold]Pilihan:[/bold]")
        console.print("[dim]1-N: Detail | n/p: Halaman | f: Filter | c: Clear | e: Export CSV | 0: Kembali[/dim]")
        
        choice = click.prompt("Pilih", type=str, default="0")
        
        if choice == "0":
            break
        elif choice.lower() == "n":
            if page < total_page:
                page += 1
        elif choice.lower() == "p":
            if page > 1:
                page -= 1
        elif choice.lower() == "f":
            filters = _set_full_filters()
            page = 1
        elif choice.lower() == "c":
            filters = {}
            page = 1
        elif choice.lower() == "e":
            export_katalog_to_csv(items)
            _wait_for_enter()
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(items):
                    lot_id = items[idx - 1].get("lotLelangId")
                    if lot_id:
                        _view_lot_detail(lot_id)
            except ValueError:
                pass


def _set_basic_filters() -> dict:
    """Set basic filters (price, area)"""
    console.print("\n[bold cyan]🔧 SET FILTER[/bold cyan]")
    
    filters = {}
    
    if click.confirm("Filter harga?", default=False):
        filters["limit_bawah"] = click.prompt("Harga min (Rp)", type=int, default=0)
        filters["limit_atas"] = click.prompt("Harga max (Rp)", type=int, default=999999999999)
    
    if click.confirm("Filter luas?", default=False):
        filters["luas_lower"] = click.prompt("Luas min (m²)", type=int, default=0)
        filters["luas_upper"] = click.prompt("Luas max (m²)", type=int, default=999999)
    
    print_success("Filter diterapkan!")
    return filters


def _set_full_filters() -> dict:
    """Set full filters including location and category"""
    console.print("\n[bold cyan]🔧 SET FILTER LENGKAP[/bold cyan]")
    
    filters = {}
    
    # Price
    if click.confirm("Filter harga?", default=False):
        filters["limit_bawah"] = click.prompt("Harga min (Rp)", type=int, default=0)
        filters["limit_atas"] = click.prompt("Harga max (Rp)", type=int, default=999999999999)
    
    # Area
    if click.confirm("Filter luas?", default=False):
        filters["luas_lower"] = click.prompt("Luas min (m²)", type=int, default=0)
        filters["luas_upper"] = click.prompt("Luas max (m²)", type=int, default=999999)
    
    # Category
    if click.confirm("Filter kategori?", default=False):
        kategori_data = api_client.get_kategori_list()
        if kategori_data and kategori_data.get("code") == 200:
            kategori_items = print_kategori_list(kategori_data)
            if kategori_items:
                choice = click.prompt("Pilih nomor (pisah koma)", default="")
                if choice:
                    try:
                        indices = [int(x.strip()) for x in choice.split(",")]
                        selected = [kategori_items[i-1].get("nama") for i in indices if 1 <= i <= len(kategori_items)]
                        if selected:
                            filters["kategori"] = selected
                    except:
                        pass
    
    # Province / City
    if click.confirm("Filter lokasi?", default=False):
        provinsi_data = api_client.get_provinsi_list()
        if provinsi_data and provinsi_data.get("code") == 200:
            prov_items = print_provinsi_list(provinsi_data)
            if prov_items:
                prov_choice = click.prompt("Pilih nomor provinsi (0 skip)", type=int, default=0)
                if 1 <= prov_choice <= len(prov_items):
                    prov_id = prov_items[prov_choice - 1].get("id")
                    filters["province"] = prov_id
                    
                    # Get cities
                    kota_data = api_client.get_kota_list(prov_id)
                    if kota_data and kota_data.get("code") == 200:
                        kota_items = print_kota_list(kota_data)
                        if kota_items:
                            kota_choice = click.prompt("Pilih nomor kota (pisah koma, 0 skip)", default="0")
                            if kota_choice != "0":
                                try:
                                    indices = [int(x.strip()) for x in kota_choice.split(",")]
                                    selected = [kota_items[i-1].get("id") for i in indices if 1 <= i <= len(kota_items)]
                                    if selected:
                                        filters["lokasi"] = selected
                                except:
                                    pass
    
    print_success("Filter diterapkan!")
    return filters


def _view_lot_detail(lot_id: str):
    """View lot detail from public API"""
    clear_screen()
    console.print(f"\n[bold cyan]🕐 {get_server_time_str()}[/bold cyan]")
    
    print_info("Mengambil detail lot...")
    data = api_client.get_lot_info(lot_id)
    
    if data and data.get("code") == 200:
        print_lot_info_public(data, api_client)
    else:
        print_error("Gagal mengambil detail.")
    
    _wait_for_enter()


if __name__ == "__main__":
    cli()
