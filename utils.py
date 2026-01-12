"""
Utility functions for Lelang CLI
"""
import re
import csv
import os
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from datetime import datetime
from config import PHOTO_BASE_URL, WEB_BASE_URL

console = Console()


def print_success(message: str):
    """Print success message in green"""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str):
    """Print error message in red"""
    console.print(f"[bold red]✗[/bold red] {message}")


def print_warning(message: str):
    """Print warning message in yellow"""
    console.print(f"[bold yellow]![/bold yellow] {message}")


def print_info(message: str):
    """Print info message in blue"""
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def format_date(date_str: str) -> str:
    """Format ISO date string to readable format"""
    if not date_str:
        return "-"
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return date_str


def format_currency(value: str | int | float) -> str:
    """Format number as Indonesian Rupiah (short)"""
    try:
        num = int(float(value))
        if num >= 1_000_000_000:
            return f"Rp {num/1_000_000_000:.1f}M"
        elif num >= 1_000_000:
            return f"Rp {num/1_000_000:.0f}jt"
        else:
            return f"Rp {num:,.0f}".replace(",", ".")
    except Exception:
        return str(value)


def format_currency_full(value: str | int | float) -> str:
    """Format number as Indonesian Rupiah (full format)"""
    try:
        num = int(float(value))
        return f"Rp {num:,.0f}".replace(",", ".")
    except Exception:
        return str(value)


def strip_html(text: str) -> str:
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    return clean


def get_status_color(status: str) -> str:
    """Get color based on auction status"""
    status_upper = status.upper() if status else ""
    
    if "LAKU" in status_upper:
        return "green"
    elif "MENANG" in status_upper:
        return "bright_green"
    elif "MULAI" in status_upper or "PENAWARAN" in status_upper:
        return "cyan"
    elif "MENUNGGU" in status_upper:
        return "yellow"
    elif "WANPRESTASI" in status_upper or "BATAL" in status_upper:
        return "red"
    elif "PAID" in status_upper:
        return "green"
    elif "UNPAID" in status_upper:
        return "yellow"
    elif "TAYANG" in status_upper:
        return "cyan"
    else:
        return "white"


def print_user_profile(data: dict):
    """Pretty print user profile data"""
    user = data.get("data", {})
    
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Nama", user.get("nama", "-"))
    table.add_row("Email", user.get("email", "-"))
    table.add_row("Username", user.get("username", "-"))
    table.add_row("Tipe User", user.get("tipeUser", "-"))
    table.add_row("Status", "[green]Aktif[/green]" if user.get("active") else "[red]Tidak Aktif[/red]")
    table.add_row("Verifikasi KTP", "[green]✓[/green]" if user.get("verifikasiKtp") else "[red]✗[/red]")
    
    perseorangan = user.get("perseorangan", {})
    if perseorangan:
        table.add_row("─" * 20, "─" * 30)
        table.add_row("No. Telepon", perseorangan.get("nomorTelepon", "-"))
        table.add_row("Alamat", perseorangan.get("alamat", "-"))
    
    console.print(Panel(table, title="[bold cyan]Profil Pengguna[/bold cyan]", border_style="cyan"))


def print_lelang_list(data: dict) -> list:
    """Pretty print list of user's auctions with selection numbers"""
    items = data.get("data", [])
    total_pages = data.get("totalPages", 1)
    total_rows = data.get("totalRows", 0)
    
    if not items:
        print_warning("Tidak ada lelang ditemukan.")
        return []
    
    table = Table(
        title=f"[bold]Lelang Saya[/bold] (Total: {total_rows})",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("No", style="bold yellow", width=4)
    table.add_column("Kode", style="cyan", width=8)
    table.add_column("Nama Lot", style="white", width=35)
    table.add_column("Nilai Limit", style="green", width=14, justify="right")
    table.add_column("Status Lelang", width=15)
    table.add_column("Status Peserta", width=18)
    table.add_column("Selesai", style="yellow", width=16)
    
    for idx, item in enumerate(items, 1):
        status_lelang = item.get("status_lelang", "-")
        status_peserta = item.get("status_peserta", "-")
        
        status_lelang_display = f"[{get_status_color(status_lelang)}]{status_lelang}[/{get_status_color(status_lelang)}]"
        status_peserta_display = f"[{get_status_color(status_peserta)}]{status_peserta}[/{get_status_color(status_peserta)}]"
        
        nama = strip_html(item.get("nama_lot_lelang", "-"))
        if len(nama) > 33:
            nama = nama[:30] + "..."
        
        table.add_row(
            f"[{idx}]",
            item.get("kode_lot", "-"),
            nama,
            format_currency(item.get("nilai_limit", 0)),
            status_lelang_display,
            status_peserta_display,
            format_date(item.get("batas_akhir_penawaran", ""))
        )
    
    console.print(table)
    console.print(f"\n[dim]Halaman: {total_pages} | Total: {total_rows}[/dim]")
    
    return items


def print_lelang_detail(data: dict):
    """Pretty print auction detail with improved layout"""
    if not data:
        print_error("Data tidak ditemukan.")
        return
    
    status_data = data.get("status", data.get("data", {}))
    lot_lelang = data.get("lotLelang", {})
    
    # STATUS SECTION
    status_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    status_table.add_column("Field", style="cyan", width=25)
    status_table.add_column("Value", style="white", width=55)
    
    status_lelang = status_data.get("statusLelang", "-")
    status_peserta = status_data.get("statusPeserta", "-")
    status_ujl = status_data.get("statusUangJaminan", "-")
    
    status_table.add_row("[bold]Status Lelang[/bold]", f"[bold {get_status_color(status_lelang)}]{status_lelang}[/bold {get_status_color(status_lelang)}]")
    status_table.add_row("[bold]Status Peserta[/bold]", f"[bold {get_status_color(status_peserta)}]{status_peserta}[/bold {get_status_color(status_peserta)}]")
    status_table.add_row("[bold]Status Uang Jaminan[/bold]", f"[{get_status_color(status_ujl)}]{status_ujl}[/{get_status_color(status_ujl)}]")
    
    status_table.add_row("", "")
    status_table.add_row("Uang Jaminan", format_currency_full(status_data.get("uangJaminan", 0)))
    
    va_info = status_data.get("va", {})
    if va_info and va_info.get("no"):
        status_table.add_row("", "")
        status_table.add_row("[bold cyan]VIRTUAL ACCOUNT[/bold cyan]", "")
        status_table.add_row("Bank", va_info.get("bank", "-"))
        status_table.add_row("No. VA", f"[bold yellow]{va_info.get('no', '-')}[/bold yellow]")
        status_table.add_row("Atas Nama", va_info.get("an", "-").strip())
    
    console.print(Panel(status_table, title="[bold cyan]📊 STATUS LELANG[/bold cyan]", border_style="cyan"))
    
    if lot_lelang:
        _print_lot_info_section(lot_lelang)


def _print_lot_info_section(lot_lelang: dict):
    """Print lot information section"""
    lot_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    lot_table.add_column("Field", style="cyan", width=25)
    lot_table.add_column("Value", style="white", width=55)
    
    lot_table.add_row("Kode Lot", f"[bold]{lot_lelang.get('kodeLot', '-')}[/bold]")
    lot_table.add_row("Nama Lot", strip_html(lot_lelang.get("namaLotLelang", "-")))
    
    # Web link - check multiple field locations
    unit_kerja_id = (
        lot_lelang.get("unitKerjaId") or 
        lot_lelang.get("unitKerja", {}).get("id") or
        lot_lelang.get("content", {}).get("organizer", {}).get("unitKerjaId") or
        ""
    )
    lot_lelang_id = lot_lelang.get("lotLelangId") or lot_lelang.get("id") or ""
    if unit_kerja_id and lot_lelang_id:
        web_url = f"{WEB_BASE_URL}/kpknl/{unit_kerja_id}/detail-auction/{lot_lelang_id}"
        lot_table.add_row("🔗 Link", f"[link={web_url}][bold blue]Klik Disini Untuk Melihat Detail[/bold blue][/link]")
    
    lot_table.add_row("", "")
    lot_table.add_row("[bold]FINANSIAL[/bold]", "")
    lot_table.add_row("Nilai Limit", format_currency_full(lot_lelang.get("nilaiLimit", 0)))
    lot_table.add_row("Uang Jaminan", format_currency_full(lot_lelang.get("uangJaminan", 0)))
    lot_table.add_row("Kelipatan Bid", format_currency_full(lot_lelang.get("kelipatanBid", 0)))
    
    lot_table.add_row("", "")
    lot_table.add_row("[bold]JADWAL[/bold]", "")
    lot_table.add_row("Mulai Lelang", format_date(lot_lelang.get("tglMulaiLelang", "")))
    lot_table.add_row("Selesai Lelang", format_date(lot_lelang.get("tglSelesaiLelang", "")))
    lot_table.add_row("Batas Jaminan", format_date(lot_lelang.get("tanggalBatasJaminan", "")))
    
    lot_table.add_row("", "")
    lot_table.add_row("[bold]LOKASI & JENIS[/bold]", "")
    lot_table.add_row("Lokasi", lot_lelang.get("namaLokasi", "-") or "-")
    lot_table.add_row("Unit Kerja", lot_lelang.get("namaUnitKerja", "-") or "-")
    lot_table.add_row("Cara Penawaran", lot_lelang.get("caraPenawaran", "-") or "-")
    
    console.print(Panel(lot_table, title="[bold cyan]📦 INFORMASI LOT[/bold cyan]", border_style="cyan"))
    
    content = lot_lelang.get("content", {})
    if content:
        _print_barang_detail_section(content.get("barangs", []))
        _print_seller_section(content.get("seller", {}))


def _print_barang_detail_section(barangs: list):
    """Print detailed barang (items) section with full info"""
    if not barangs:
        return
    
    for i, barang in enumerate(barangs):
        barang_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
        barang_table.add_column("Field", style="cyan", width=22)
        barang_table.add_column("Value", style="white", width=55)
        
        nama = strip_html(barang.get("nama", "-")) or f"Barang #{i+1}"
        barang_table.add_row("[bold]Nama[/bold]", nama)
        
        # Jenis
        jenis_barang = barang.get("jenisBarang", {})
        jenis_objek = barang.get("jenisObjek", {})
        if jenis_barang:
            barang_table.add_row("Jenis Barang", jenis_barang.get("nama", "-"))
        if jenis_objek:
            barang_table.add_row("Jenis Objek", jenis_objek.get("nama", "-"))
        
        # Bukti Kepemilikan
        bukti = barang.get("buktiKepemilikan", "")
        if bukti:
            barang_table.add_row("Bukti Kepemilikan", bukti)
        bukti_no = barang.get("buktiKepemilikanNo", "")
        if bukti_no:
            barang_table.add_row("No. Bukti", bukti_no)
        bukti_tgl = barang.get("buktiKepemilikanTgl", "")
        if bukti_tgl:
            barang_table.add_row("Tgl. Bukti", format_date(bukti_tgl))
        
        # Alamat
        alamat = barang.get("alamat", "")
        if alamat:
            barang_table.add_row("Alamat", alamat)
        
        # Luas
        luas = barang.get("luas", "")
        if luas:
            barang_table.add_row("Luas", f"{luas} m²")
        
        # Kendaraan info
        nopol = barang.get("nopol", "")
        if nopol:
            barang_table.add_row("Nopol", nopol)
        
        stnk = barang.get("stnk", "")
        if stnk:
            barang_table.add_row("STNK", stnk)
        
        no_rangka = barang.get("nomorRangka", "")
        if no_rangka:
            barang_table.add_row("No. Rangka", no_rangka)
        
        tahun = barang.get("tahun", "")
        if tahun:
            barang_table.add_row("Tahun", tahun)
        
        warna = barang.get("warna", "")
        if warna:
            barang_table.add_row("Warna", warna)
        
        # Photos count
        photos = barang.get("photos", [])
        if photos:
            barang_table.add_row("Foto", f"{len(photos)} gambar tersedia")
        
        console.print(Panel(barang_table, title=f"[bold cyan]🏷️ BARANG #{i+1}[/bold cyan]", border_style="cyan"))


def _print_seller_section(seller: dict):
    """Print seller information"""
    if not seller or not (seller.get("namaPenjual") or seller.get("namaOrganisasiPenjual")):
        return
    
    seller_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    seller_table.add_column("Field", style="cyan", width=22)
    seller_table.add_column("Value", style="white", width=55)
    
    seller_table.add_row("Nama", seller.get("namaPenjual", "-") or "-")
    seller_table.add_row("Organisasi", seller.get("namaOrganisasiPenjual", "-") or "-")
    seller_table.add_row("Telepon", seller.get("nomorTelepon", "-") or "-")
    seller_table.add_row("Alamat", seller.get("alamat", "-") or "-")
    
    console.print(Panel(seller_table, title="[bold cyan]🏢 PENJUAL[/bold cyan]", border_style="cyan"))


# ==================== BROWSE LELANG FUNCTIONS ====================

def print_kpknl_list(data: dict) -> list:
    """Print list of KPKNL offices with selection numbers"""
    items = data.get("data", [])
    
    if not items:
        print_warning("Tidak ada data KPKNL ditemukan.")
        return []
    
    table = Table(
        title=f"[bold]Daftar KPKNL[/bold] (Total: {len(items)})",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("No", style="bold yellow", width=4)
    table.add_column("Nama KPKNL", style="cyan", width=22)
    table.add_column("Kota", style="white", width=20)
    table.add_column("Propinsi", style="white", width=20)
    table.add_column("Telepon", style="dim", width=15)
    
    for idx, item in enumerate(items, 1):
        table.add_row(
            f"[{idx}]",
            item.get("nama", "-"),
            item.get("kota", "-"),
            item.get("propinsi", "-"),
            item.get("telepon", "-")
        )
    
    console.print(table)
    return items


def print_katalog_list(data: dict, show_link: bool = True) -> list:
    """Print katalog lot lelang with selection numbers"""
    items = data.get("data", [])
    page = data.get("page", 1)
    total_page = data.get("totalPage", 1)
    total_item = data.get("totalItem", 0)
    
    if not items:
        print_warning("Tidak ada lot lelang ditemukan.")
        return []
    
    console.print(f"\n[bold cyan]📋 KATALOG LOT LELANG[/bold cyan] | Halaman {page}/{total_page} | Total: {total_item}")
    console.print("─" * 85)
    
    for idx, item in enumerate(items, 1):
        nama = strip_html(item.get("namaLotLelang", "-"))
        if len(nama) > 55:
            nama = nama[:52] + "..."
        
        nilai_limit = format_currency(item.get("nilaiLimit", 0))
        uang_jaminan = format_currency(item.get("uangJaminan", 0))
        lokasi = item.get("namaLokasi", "-")
        unit_kerja = item.get("namaUnitKerja", "-")
        selesai = format_date(item.get("tglSelesaiLelang", ""))
        status = item.get("status", "-")
        cara = item.get("caraPenawaran", "-")
        
        photos = item.get("photos", [])
        photo_count = len(photos)
        
        status_color = get_status_color(status)
        
        console.print(f"\n[bold yellow][{idx}][/bold yellow] [bold]{nama}[/bold]")
        console.print(f"    💰 Limit: [green]{nilai_limit}[/green] | Jaminan: [yellow]{uang_jaminan}[/yellow]")
        console.print(f"    📍 {lokasi} | 🏛️ {unit_kerja}")
        console.print(f"    ⏰ Selesai: [cyan]{selesai}[/cyan] | [{status_color}]{status}[/{status_color}] | {cara}")
        
        if photo_count > 0:
            console.print(f"    📷 {photo_count} foto")
        
        # Web link
        if show_link:
            unit_id = item.get("unitKerjaId", "")
            lot_id = item.get("lotLelangId", "")
            if unit_id and lot_id:
                url = f"{WEB_BASE_URL}/kpknl/{unit_id}/detail-auction/{lot_id}"
                console.print(f"    🔗 [dim blue]{url}[/dim blue]")
    
    console.print("\n" + "─" * 85)
    console.print(f"[dim]Halaman {page}/{total_page} | Total: {total_item} lot[/dim]")
    
    return items


def print_lot_info_public(data: dict, api_client=None):
    """Print detailed lot info from public API with photo URLs"""
    if not data or data.get("code") != 200:
        print_error("Data tidak ditemukan.")
        return
    
    lot = data.get("data", {})
    
    lot_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    lot_table.add_column("Field", style="cyan", width=22)
    lot_table.add_column("Value", style="white", width=55)
    
    lot_table.add_row("[bold]INFORMASI LOT[/bold]", "")
    lot_table.add_row("Kode Lot", f"[bold]{lot.get('kodeLot', '-')}[/bold]")
    lot_table.add_row("Nama Lot", strip_html(lot.get("namaLotLelang", "-")))
    lot_table.add_row("Status", f"[{get_status_color(lot.get('status', ''))}]{lot.get('status', '-')}[/{get_status_color(lot.get('status', ''))}]")
    
    # Web link - check multiple field locations
    # From katalog: unitKerjaId, lotLelangId
    # From lot info: id (as lotLelangId), unitKerjaId or organizer.unitKerjaId
    unit_id = (
        lot.get("unitKerjaId") or 
        lot.get("unitKerja", {}).get("id") or
        lot.get("organizer", {}).get("unitKerjaId") or
        lot.get("content", {}).get("organizer", {}).get("unitKerjaId") or
        ""
    )
    lot_lelang_id = lot.get("lotLelangId") or lot.get("id") or ""
    
    if unit_id and lot_lelang_id:
        web_url = f"{WEB_BASE_URL}/kpknl/{unit_id}/detail-auction/{lot_lelang_id}"
        lot_table.add_row("🔗 Link Web", f"[link={web_url}][bold blue]Klik Disini Untuk Melihat Detail[/bold blue][/link]")
    
    lot_table.add_row("", "")
    lot_table.add_row("[bold]FINANSIAL[/bold]", "")
    lot_table.add_row("Nilai Limit", format_currency_full(lot.get("nilaiLimit", 0)))
    lot_table.add_row("Uang Jaminan", format_currency_full(lot.get("uangJaminan", 0)))
    lot_table.add_row("Kelipatan Bid", format_currency_full(lot.get("kelipatanBid", 0)))
    
    lot_table.add_row("", "")
    lot_table.add_row("[bold]JADWAL[/bold]", "")
    lot_table.add_row("Mulai Lelang", format_date(lot.get("tglMulaiLelang", "")))
    lot_table.add_row("Selesai Lelang", format_date(lot.get("tglSelesaiLelang", "")))
    lot_table.add_row("Batas Jaminan", format_date(lot.get("tanggalBatasJaminan", "")))
    
    lot_table.add_row("", "")
    lot_table.add_row("[bold]LOKASI & JENIS[/bold]", "")
    lot_table.add_row("Lokasi", lot.get("namaLokasi", "-") or "-")
    lot_table.add_row("Unit Kerja", lot.get("namaUnitKerja", "-") or "-")
    lot_table.add_row("Cara Penawaran", lot.get("caraPenawaran", "-") or "-")
    lot_table.add_row("Kategori", lot.get("namaKategoriLelang", "-") or "-")
    
    console.print(Panel(lot_table, title="[bold cyan]📦 DETAIL LOT LELANG[/bold cyan]", border_style="cyan"))
    
    # Print barang details - check multiple locations
    barangs = lot.get("barangs", [])
    if not barangs:
        # Try from content wrapper
        content = lot.get("content", {})
        barangs = content.get("barangs", [])
    if barangs:
        _print_barang_detail_section(barangs)
    
    # Print photos with actual URLs
    photos = lot.get("photos", [])
    if photos:
        print_photos_with_urls(photos, api_client)


def print_photos_with_urls(photos: list, api_client=None):
    """Print photos with resolved URLs from API"""
    if not photos:
        return
    
    console.print(f"\n[bold cyan]📷 FOTO ({len(photos)} gambar)[/bold cyan]")
    
    for i, photo in enumerate(photos):
        file_info = photo.get("file", {})
        file_id = file_info.get("id", "")
        file_name = file_info.get("fileName", "-")
        is_cover = " [yellow]★ Cover[/yellow]" if photo.get("iscover") else ""
        
        console.print(f"  [{i+1}]{is_cover} {file_name[:45]}")
        
        # Try to get actual URL if api_client is provided
        if api_client and file_id:
            url = api_client.get_photo_url(file_id)
            if url:
                console.print(f"      [blue]{url}[/blue]")
            else:
                # Fallback to constructed URL
                file_url = file_info.get("fileUrl", "")
                if file_url:
                    console.print(f"      [dim]{PHOTO_BASE_URL}{file_url}[/dim]")
        else:
            file_url = file_info.get("fileUrl", "")
            if file_url:
                console.print(f"      [dim]{PHOTO_BASE_URL}{file_url}[/dim]")


def print_kategori_list(data: dict) -> list:
    """Print list of categories with selection numbers"""
    items = data.get("data", [])
    
    if not items:
        print_warning("Tidak ada kategori ditemukan.")
        return []
    
    console.print("\n[bold cyan]📁 KATEGORI LELANG[/bold cyan]")
    
    for idx, item in enumerate(items, 1):
        nama = item.get("nama", "-")
        console.print(f"  [{idx}] {nama}")
    
    return items


def print_provinsi_list(data: dict) -> list:
    """Print list of provinces with selection numbers"""
    items = data.get("data", [])
    
    if not items:
        return []
    
    console.print("\n[bold cyan]📍 PROVINSI[/bold cyan]")
    
    for idx, item in enumerate(items[:34], 1):  # Show first 34
        nama = item.get("nama", "-")
        console.print(f"  [{idx}] {nama}")
    
    if len(items) > 34:
        console.print(f"  ... dan {len(items) - 34} lainnya")
    
    return items


def print_kota_list(data: dict) -> list:
    """Print list of cities with selection numbers"""
    items = data.get("data", [])
    
    if not items:
        return []
    
    console.print("\n[bold cyan]🏙️ KOTA/KABUPATEN[/bold cyan]")
    
    for idx, item in enumerate(items[:20], 1):  # Show first 20
        nama = item.get("nama", "-")
        console.print(f"  [{idx}] {nama}")
    
    if len(items) > 20:
        console.print(f"  ... dan {len(items) - 20} lainnya")
    
    return items


def print_server_time_header(time_str: str):
    """Print server time in header style"""
    console.print(f"[dim]🕐 Server Time: [bold cyan]{time_str}[/bold cyan][/dim]")


def export_katalog_to_csv(items: list, filename: str = None) -> str:
    """
    Export katalog items to CSV file
    Returns the full path to the saved file
    """
    if not items:
        print_warning("Tidak ada data untuk di-export.")
        return ""
    
    # Generate filename with timestamp if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"katalog_lelang_{timestamp}.csv"
    
    # Ensure .csv extension
    if not filename.endswith(".csv"):
        filename += ".csv"
    
    # Save to current directory or user's home
    filepath = os.path.join(os.getcwd(), filename)
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'No',
                'Kode Lot',
                'Nama Lot',
                'Nilai Limit',
                'Uang Jaminan',
                'Lokasi',
                'Unit Kerja',
                'Tanggal Selesai',
                'Status',
                'Cara Penawaran',
                'Link'
            ])
            
            # Data rows
            for idx, item in enumerate(items, 1):
                nama = strip_html(item.get("namaLotLelang", "-"))
                nilai_limit = item.get("nilaiLimit", 0)
                uang_jaminan = item.get("uangJaminan", 0)
                lokasi = item.get("namaLokasi", "-")
                unit_kerja = item.get("namaUnitKerja", "-")
                tanggal_selesai = item.get("tglSelesaiLelang", "-")
                status = item.get("status", "-")
                cara = item.get("caraPenawaran", "-")
                
                # Build link
                unit_id = item.get("unitKerjaId", "")
                lot_id = item.get("lotLelangId", "")
                link = f"{WEB_BASE_URL}/kpknl/{unit_id}/detail-auction/{lot_id}" if unit_id and lot_id else "-"
                
                writer.writerow([
                    idx,
                    item.get("kodeLot", "-"),
                    nama,
                    nilai_limit,
                    uang_jaminan,
                    lokasi,
                    unit_kerja,
                    tanggal_selesai,
                    status,
                    cara,
                    link
                ])
        
        print_success(f"Data berhasil di-export ke: {filepath}")
        return filepath
        
    except Exception as e:
        print_error(f"Gagal export CSV: {e}")
        return ""


def print_bid_history(data: dict) -> list:
    """Print bid history with table format"""
    items = data.get("data", [])
    
    if not items:
        print_warning("Tidak ada riwayat penawaran.")
        return []
    
    table = Table(
        title="[bold]Riwayat Penawaran[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("No", style="bold yellow", width=4)
    table.add_column("Waktu", style="cyan", width=22)
    table.add_column("Nilai Penawaran", style="green", width=18, justify="right")
    table.add_column("User Auction ID", style="dim", width=36)
    
    for idx, item in enumerate(items, 1):
        bid_amount = format_currency_full(item.get("bidAmount", 0))
        bid_time = format_date(item.get("time", ""))
        user_auction_id = item.get("userAuctionId", "-")
        
        table.add_row(
            str(idx),
            bid_time,
            bid_amount,
            user_auction_id[:36]
        )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(items)} penawaran[/dim]")
    
    return items


def print_bidding_info(status_data: dict, lot_lelang: dict = None):
    """Print bidding info including PIN"""
    if not status_data:
        print_error("Data tidak ditemukan.")
        return
    
    # Extract data from nested structure
    data = status_data.get("data", status_data)
    status = data.get("status", data)
    lot = data.get("lotLelang", lot_lelang or {})
    # PIN is in data.peserta.pinBidding
    peserta = data.get("peserta", {})
    
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Field", style="cyan", width=22)
    table.add_column("Value", style="white", width=40)
    
    # PIN Bidding from peserta
    pin = peserta.get("pinBidding", "-")
    table.add_row("[bold]PIN Bidding[/bold]", f"[bold yellow]{pin}[/bold yellow]")
    
    # Status info
    table.add_row("Status Lelang", f"[{get_status_color(status.get('statusLelang', ''))}]{status.get('statusLelang', '-')}[/{get_status_color(status.get('statusLelang', ''))}]")
    table.add_row("Status Peserta", f"[{get_status_color(status.get('statusPeserta', ''))}]{status.get('statusPeserta', '-')}[/{get_status_color(status.get('statusPeserta', ''))}]")
    
    # Lot info
    if lot:
        table.add_row("", "")
        table.add_row("[bold]INFORMASI BID[/bold]", "")
        table.add_row("Nilai Limit", format_currency_full(lot.get("nilaiLimit", 0)))
        table.add_row("Kelipatan Bid", format_currency_full(lot.get("kelipatanBid", 0)))
    
    console.print(Panel(table, title="[bold cyan]🎯 INFO BIDDING[/bold cyan]", border_style="cyan"))
    
    return pin, lot.get("kelipatanBid", 0) if lot else 0

