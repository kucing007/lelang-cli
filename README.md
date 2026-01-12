# Lelang CLI - Bot Autobid

CLI application untuk lelang.go.id dengan fitur Bot Autobid yang ultra-cepat.

## Fitur

- 🔐 Login dengan username/password
- 📋 Browse katalog lelang
- 📦 Lihat lelang saya
- 🤖 **Bot Autobid** dengan burst polling (10-500ms interval)
- ⚡ Async concurrent polling (3 parallel requests)
- ⏱️ Live countdown timer
- 🎯 Deteksi penawaran terakhir real-time

## Instalasi

```bash
pip install -r requirements.txt
```

## Penggunaan

```bash
# Interactive mode
python main.py interactive

# Login
python main.py login

# Cek profile
python main.py profile
```

## Bot Autobid

1. Jalankan `python main.py interactive`
2. Pilih **Lelang Saya** → lelang dengan status Peserta Bidding
3. Pilih **Mulai Lelang** → **Bot Autobid**
4. Masukkan budget maksimal
5. Bot akan otomatis bid saat ada penawaran baru

## Konfigurasi

- **Polling interval**: 10-500ms (default 20ms)
- **Concurrent requests**: 3 parallel requests
- **Auto-stop**: Saat budget exceeded atau lelang selesai

## Performa

| Metric | Lokal | VPS Jakarta |
|--------|-------|-------------|
| Response | ~138ms | ~25-35ms |
| Bid/detik | ~7 | ~30-40 |

## Requirements

- Python 3.10+
- httpx
- rich
- click
