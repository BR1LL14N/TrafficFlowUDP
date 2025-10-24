# bmkg_udp_server.py
import socket
import threading
import time
import requests
from bs4 import BeautifulSoup

# === Konfigurasi ===
SERVER_PORT = 5000          # Port UDP server untuk menerima JOIN
UPDATE_INTERVAL = 60        # Update tiap 60 detik
BMKG_URL = "https://www.bmkg.go.id/alerts/nowcast/id"

# Simpan daftar client: {(ip, port)}
clients = set()
clients_lock = threading.Lock()

def fetch_bmkg_weather():
    """Ambil dan ekstrak ringkasan cuaca dari halaman BMKG."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (WeatherClient; Python)"
        }
        response = requests.get(BMKG_URL, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Cari elemen utama yang berisi informasi nowcast
        # BMKG sering pakai <div class="col-md-12"> atau <p> di dalam alert box
        # Kita coba ambil teks dari paragraf pertama di halaman
        main_content = soup.find('div', class_='col-md-12')
        if not main_content:
            main_content = soup.find('div', class_='container')

        if main_content:
            # Ambil semua teks paragraf
            paragraphs = main_content.find_all('p')
            if paragraphs:
                # Ambil paragraf pertama yang tidak kosong
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:  # hindari teks terlalu pendek
                        # Potong agar tidak terlalu panjang untuk UDP
                        return f"🌦️ BMKG Nowcast: {text[:200]}..."
        
        # Fallback: ambil judul halaman
        title = soup.title.string if soup.title else "Peringatan Dini Cuaca"
        return f"🌦️ {title.strip()} - Data dari BMKG"

    except Exception as e:
        return f"⚠️ Gagal ambil data BMKG: {str(e)[:100]}"

def handle_client_registration():
    """Terima paket JOIN dari client dan simpan alamatnya."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", SERVER_PORT))
    print(f"[SERVER] Menunggu client JOIN di port UDP {SERVER_PORT}...")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode('utf-8', errors='ignore').strip()
            if message == "JOIN":
                with clients_lock:
                    clients.add(addr)
                print(f"[SERVER] Client baru: {addr}")
        except Exception as e:
            print(f"[ERROR] Gagal terima JOIN: {e}")

def broadcast_weather():
    """Ambil cuaca dan kirim ke semua client terdaftar."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        weather_msg = fetch_bmkg_weather()
        print(f"\n[SERVER] Update cuaca:\n{weather_msg}\n")

        with clients_lock:
            active_clients = list(clients)
            dead_clients = []

        # Kirim ke setiap client
        for client_addr in active_clients:
            try:
                sock.sendto(weather_msg.encode('utf-8'), client_addr)
            except Exception as e:
                print(f"[SERVER] Gagal kirim ke {client_addr}: {e}")
                dead_clients.append(client_addr)

        # Hapus client yang error (opsional)
        if dead_clients:
            with clients_lock:
                for dc in dead_clients:
                    clients.discard(dc)

        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    # Jalankan listener JOIN di thread terpisah
    threading.Thread(target=handle_client_registration, daemon=True).start()
    print("[SERVER] Server BMKG UDP siap.")
    broadcast_weather()
    