"""
Configuration for Lelang CLI Application
"""
import os
from pathlib import Path

# API Base URLs
API_AUTH_BASE_URL = "https://api-auth.lelang.go.id/api/v1"
API_AUTH_TOKEN_URL = "https://api-auth.lelang.go.id/api/token"
API_LELANG_BASE_URL = "https://api.lelang.go.id/api/v1"
WEB_BASE_URL = "https://lelang.go.id"

# Auth Endpoints
LOGIN_ENDPOINT = f"{API_AUTH_BASE_URL}/login"
ME_ENDPOINT = f"{API_AUTH_BASE_URL}/me"
REFRESH_TOKEN_ENDPOINT = f"{API_AUTH_TOKEN_URL}/refresh"

# Lelang Saya Endpoints (authenticated)
LELANG_SAYA_ENDPOINT = f"{API_LELANG_BASE_URL}/pelaksanaan/daftar-status-lelangs"
LELANG_DETAIL_ENDPOINT = f"{API_LELANG_BASE_URL}/pelaksanaan"  # /{lot_lelang_id}/status-lelang

# Browse Lelang Endpoints (public)
KPKNL_LIST_ENDPOINT = f"{API_LELANG_BASE_URL}/landing-page/kpknl"
KATALOG_KPKNL_ENDPOINT = f"{API_LELANG_BASE_URL}/landing-page-kpknl"  # /{kpknl_id}/katalog-lot-lelang
KATALOG_UMUM_ENDPOINT = f"{API_LELANG_BASE_URL}/landing-page/katalog-lot-lelang"  # Updated!
LOT_INFO_ENDPOINT = f"{API_LELANG_BASE_URL}/landing-page/info"  # /{lotLelangId}
KATEGORI_ENDPOINT = f"{API_LELANG_BASE_URL}/landing-page/kategori"

# Media/Photo URL Endpoint
MEDIA_URL_ENDPOINT = f"{API_LELANG_BASE_URL}/mediaById"  # /{file_id}/object-url

# Reference Data Endpoints
REF_PROVINSI_ENDPOINT = f"{API_AUTH_BASE_URL}/master/ref-provinsi"
REF_KOTA_ENDPOINT = f"{API_AUTH_BASE_URL}/master/ref-kota"

# Bidding API (bidding.lelang.go.id)
BIDDING_BASE_URL = "https://bidding.lelang.go.id/api/v1"
BIDDING_START_SESSION = f"{BIDDING_BASE_URL}/pelaksanaan/lelang/mulai-sesi"
BIDDING_HISTORY = f"{BIDDING_BASE_URL}/pelaksanaan/lelang"  # /{lotLelangId}/riwayat
BIDDING_SUBMIT = f"{BIDDING_BASE_URL}/pelaksanaan/lelang/pengajuan-penawaran"

# Token Storage
HOME_DIR = Path.home()
CONFIG_DIR = HOME_DIR / ".lelang-cli"
TOKEN_FILE = CONFIG_DIR / "token.json"

# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Request Settings
REQUEST_TIMEOUT = 30  # seconds

# Browser Settings
BROWSER_HEADLESS = False  # Must be visible for captcha
LOGIN_PAGE_URL = f"{WEB_BASE_URL}/login"

# Token Refresh Settings
TOKEN_REFRESH_MIN_INTERVAL = 30   # seconds
TOKEN_REFRESH_MAX_INTERVAL = 240  # seconds

# Web URLs (for links)
LELANG_DETAIL_WEB_URL = f"{WEB_BASE_URL}/kpknl"  # /{kpknl_id}/detail-auction/{lot_lelang_id}
PHOTO_BASE_URL = "https://api.lelang.go.id"
