"""
API Client for Lelang.go.id
"""
import httpx
from config import (
    ME_ENDPOINT, REQUEST_TIMEOUT, LELANG_SAYA_ENDPOINT, LELANG_DETAIL_ENDPOINT,
    KPKNL_LIST_ENDPOINT, KATALOG_KPKNL_ENDPOINT, KATALOG_UMUM_ENDPOINT,
    LOT_INFO_ENDPOINT, KATEGORI_ENDPOINT, REF_PROVINSI_ENDPOINT, REF_KOTA_ENDPOINT,
    MEDIA_URL_ENDPOINT, BIDDING_START_SESSION, BIDDING_HISTORY, BIDDING_SUBMIT
)
from auth import get_stored_token, refresh_access_token
from utils import print_error, print_warning


class LelangAPIClient:
    """HTTP client for Lelang.go.id API"""
    
    def __init__(self):
        self.timeout = REQUEST_TIMEOUT
    
    def _get_headers(self) -> dict:
        """Get headers with authorization token"""
        token_data = get_stored_token()
        if not token_data or "access_token" not in token_data:
            raise ValueError("Token tidak ditemukan. Silakan login terlebih dahulu.")
        
        return {
            "Authorization": f"Bearer {token_data['access_token']}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _get_public_headers(self) -> dict:
        """Get headers for public API (no auth required)"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _handle_response(self, response, retry_func=None):
        """Handle API response with automatic token refresh on 401"""
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print_warning("Token expired, mencoba refresh...")
            if refresh_access_token():
                if retry_func:
                    return retry_func()
            print_error("Token expired dan gagal refresh. Silakan login ulang.")
            return None
        else:
            print_error(f"API Error: {response.status_code}")
            return None
    
    def _handle_public_response(self, response):
        """Handle public API response (no retry)"""
        if response.status_code == 200:
            return response.json()
        else:
            print_error(f"API Error: {response.status_code}")
            return None
    
    # ==================== AUTHENTICATED ENDPOINTS ====================
    
    def get_user_profile(self) -> dict | None:
        """Get current user profile"""
        try:
            headers = self._get_headers()
            
            def make_request():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(ME_ENDPOINT, headers=self._get_headers())
                    return self._handle_response(response)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(ME_ENDPOINT, headers=headers)
                return self._handle_response(response, make_request)
                    
        except ValueError as e:
            print_error(str(e))
            return None
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_lelang_saya(self, page: int = 1, limit: int = 10, search: str = "") -> dict | None:
        """Get list of user's auctions (Lelang Saya)"""
        try:
            headers = self._get_headers()
            
            params = {
                "page": page,
                "limit": limit,
                "dcp": "true",
                "search_by": "",
                "q": search
            }
            
            def make_request():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(LELANG_SAYA_ENDPOINT, headers=self._get_headers(), params=params)
                    return self._handle_response(response)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(LELANG_SAYA_ENDPOINT, headers=headers, params=params)
                return self._handle_response(response, make_request)
                    
        except ValueError as e:
            print_error(str(e))
            return None
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_lelang_detail(self, lot_lelang_id: str) -> dict | None:
        """Get auction detail status (authenticated)"""
        try:
            headers = self._get_headers()
            
            url = f"{LELANG_DETAIL_ENDPOINT}/{lot_lelang_id}/status-lelang"
            params = {"dcp": "true"}
            
            def make_request():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, headers=self._get_headers(), params=params)
                    return self._handle_response(response)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers, params=params)
                return self._handle_response(response, make_request)
                    
        except ValueError as e:
            print_error(str(e))
            return None
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None

    # ==================== PUBLIC ENDPOINTS ====================
    
    def get_kpknl_list(self, sortby: str = "nama", sortdir: str = "asc") -> dict | None:
        """Get list of all KPKNL offices"""
        try:
            headers = self._get_public_headers()
            params = {"sortby": sortby, "sortdir": sortdir}
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(KPKNL_LIST_ENDPOINT, headers=headers, params=params)
                return self._handle_public_response(response)
                    
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_katalog_kpknl(
        self, 
        kpknl_id: str,
        page: int = 1, 
        limit: int = 20,
        search: str = "",
        limit_bawah: int = None,
        limit_atas: int = None,
        luas_lower: int = None,
        luas_upper: int = None,
        kategori: list = None
    ) -> dict | None:
        """
        Get katalog lot lelang for specific KPKNL
        GET /api/v1/landing-page-kpknl/{kpknl_id}/katalog-lot-lelang
        """
        try:
            headers = self._get_public_headers()
            url = f"{KATALOG_KPKNL_ENDPOINT}/{kpknl_id}/katalog-lot-lelang"
            
            params = {
                "page": page,
                "limit": limit
            }
            
            if search:
                params["search"] = search
            if limit_bawah is not None:
                params["limitbawah"] = limit_bawah
            if limit_atas is not None:
                params["limitatas"] = limit_atas
            if luas_lower is not None:
                params["luasLowerLimit"] = luas_lower
            if luas_upper is not None:
                params["luasUpperLimit"] = luas_upper
            
            with httpx.Client(timeout=self.timeout) as client:
                if kategori:
                    kategori_params = "&".join([f"namakategori[]={k}" for k in kategori])
                    full_url = f"{url}?{kategori_params}"
                    response = client.get(full_url, headers=headers, params=params)
                else:
                    response = client.get(url, headers=headers, params=params)
                return self._handle_public_response(response)
                    
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_katalog_umum(
        self, 
        page: int = 1, 
        limit: int = 20,
        limit_bawah: int = None,
        limit_atas: int = None,
        luas_lower: int = None,
        luas_upper: int = None,
        kategori: list = None,
        lokasi: list = None,
        province: str = None
    ) -> dict | None:
        """
        Get katalog lot lelang umum (all)
        GET /api/v1/landing-page/katalog-lot-lelang
        """
        try:
            headers = self._get_public_headers()
            
            params = {
                "page": page,
                "limit": limit,
                "dcp": "true"
            }
            
            if limit_bawah is not None:
                params["limitbawah"] = limit_bawah
            if limit_atas is not None:
                params["limitatas"] = limit_atas
            if luas_lower is not None:
                params["luasLowerLimit"] = luas_lower
            if luas_upper is not None:
                params["luasUpperLimit"] = luas_upper
            if province:
                params["province"] = province
            
            with httpx.Client(timeout=self.timeout) as client:
                # Build URL with array params
                extra_params = []
                if kategori:
                    extra_params.extend([f"namakategori[]={k}" for k in kategori])
                if lokasi:
                    extra_params.extend([f"lokasi[]={l}" for l in lokasi])
                
                if extra_params:
                    full_url = f"{KATALOG_UMUM_ENDPOINT}?{'&'.join(extra_params)}"
                    response = client.get(full_url, headers=headers, params=params)
                else:
                    response = client.get(KATALOG_UMUM_ENDPOINT, headers=headers, params=params)
                return self._handle_public_response(response)
                    
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_lot_info(self, lot_lelang_id: str) -> dict | None:
        """Get lot lelang info (public)"""
        try:
            headers = self._get_public_headers()
            url = f"{LOT_INFO_ENDPOINT}/{lot_lelang_id}"
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers)
                return self._handle_public_response(response)
                    
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_photo_url(self, file_id: str) -> str | None:
        """
        Get actual photo URL from file ID
        GET /api/v1/mediaById/{file_id}/object-url
        Returns the actual URL string
        """
        try:
            headers = self._get_public_headers()
            url = f"{MEDIA_URL_ENDPOINT}/{file_id}/object-url"
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        return data.get("data", {}).get("url")
                return None
                    
        except httpx.RequestError:
            return None
    
    def get_kategori_list(self) -> dict | None:
        """Get list of auction categories"""
        try:
            headers = self._get_public_headers()
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(KATEGORI_ENDPOINT, headers=headers)
                return self._handle_public_response(response)
                    
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_provinsi_list(self) -> dict | None:
        """Get reference list of provinces"""
        try:
            headers = self._get_public_headers()
            params = {"limit": 9999}
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(REF_PROVINSI_ENDPOINT, headers=headers, params=params)
                return self._handle_public_response(response)
                    
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_kota_list(self, provinsi_id: str = None) -> dict | None:
        """Get reference list of cities"""
        try:
            headers = self._get_public_headers()
            params = {"limit": 9999}
            if provinsi_id:
                params["provinsi_id"] = provinsi_id
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(REF_KOTA_ENDPOINT, headers=headers, params=params)
                return self._handle_public_response(response)
                    
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None

    # ==================== BIDDING ENDPOINTS ====================
    
    def start_auction_session(self, lot_lelang_id: str) -> dict | None:
        """
        Start auction session (Mulai Sesi Lelang)
        POST https://bidding.lelang.go.id/api/v1/pelaksanaan/lelang/mulai-sesi
        Payload: {"auctionId": lot_lelang_id}
        """
        try:
            headers = self._get_headers()
            payload = {"auctionId": lot_lelang_id}
            
            def make_request():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(BIDDING_START_SESSION, headers=self._get_headers(), json=payload)
                    return self._handle_response(response)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(BIDDING_START_SESSION, headers=headers, json=payload)
                return self._handle_response(response, make_request)
                    
        except ValueError as e:
            print_error(str(e))
            return None
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_bid_history(self, lot_lelang_id: str) -> dict | None:
        """
        Get bid history (Riwayat Penawaran)
        GET https://bidding.lelang.go.id/api/v1/pelaksanaan/lelang/{lotLelangId}/riwayat
        """
        try:
            headers = self._get_headers()
            url = f"{BIDDING_HISTORY}/{lot_lelang_id}/riwayat"
            
            def make_request():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, headers=self._get_headers())
                    return self._handle_response(response)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers)
                return self._handle_response(response, make_request)
                    
        except ValueError as e:
            print_error(str(e))
            return None
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def get_auction_status_with_pin(self, lot_lelang_id: str) -> dict | None:
        """
        Get auction status including PIN Bidding
        GET https://api.lelang.go.id/api/v1/pelaksanaan/{lotLelangId}/status-lelang?dcp=true
        Returns data including pinBidding
        """
        try:
            headers = self._get_headers()
            url = f"https://api.lelang.go.id/api/v1/pelaksanaan/{lot_lelang_id}/status-lelang"
            params = {"dcp": "true"}
            
            def make_request():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, headers=self._get_headers(), params=params)
                    return self._handle_response(response)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers, params=params)
                return self._handle_response(response, make_request)
                    
        except ValueError as e:
            print_error(str(e))
            return None
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None
    
    def submit_bid(self, lot_lelang_id: str, bid_amount: int, pin: str, bid_time: str) -> dict | None:
        """
        Submit bid (Pengajuan Penawaran)
        POST https://bidding.lelang.go.id/api/v1/pelaksanaan/lelang/pengajuan-penawaran
        Payload: {"auctionId": lot_lelang_id, "bidAmount": bid_amount, "passkey": pin, "bidTime": bid_time}
        """
        try:
            headers = self._get_headers()
            payload = {
                "auctionId": lot_lelang_id,
                "bidAmount": bid_amount,
                "passkey": pin,
                "bidTime": bid_time
            }
            
            def make_request():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(BIDDING_SUBMIT, headers=self._get_headers(), json=payload)
                    return self._handle_response(response)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(BIDDING_SUBMIT, headers=headers, json=payload)
                return self._handle_response(response, make_request)
                    
        except ValueError as e:
            print_error(str(e))
            return None
        except httpx.RequestError as e:
            print_error(f"Network error: {e}")
            return None


# Create default client instance
api_client = LelangAPIClient()
