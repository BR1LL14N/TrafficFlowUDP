# server.py
import os
import time
import socket
import threading
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load API key
load_dotenv()
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
if not TOMTOM_API_KEY:
    raise ValueError("TOMTOM_API_KEY tidak ditemukan di .env")

# Konfigurasi
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5005
UPDATE_INTERVAL = 3.5

# --- PERUBAHAN 1: Variabel Global untuk Lokasi Dinamis ---
# Simpan lokasi yang sedang dipantau secara global
current_location = {
    # Lokasi default saat server pertama kali jalan
    "name": "Jalan Mayjen Sungkono, Surabaya",
    "lat": -7.2910,
    "lon": 112.7203
}
location_lock = threading.Lock() # Lock untuk menjaga data thread-safe

# Simpan client aktif
clients = set()
clients_lock = threading.Lock()

def geocode_address(address):
    """Mengubah alamat/nama jalan menjadi koordinat (lat, lon)."""
    geocode_url = f"https://api.tomtom.com/search/2/geocode/{address}.json"
    try:
        response = requests.get(geocode_url, params={"key": TOMTOM_API_KEY, "countrySet": "ID"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and data.get("results"):
            pos = data["results"][0]["position"]
            return pos["lat"], pos["lon"]
        return None, None
    except Exception as e:
        print(f"[GEOCODE ERROR] Gagal mengubah alamat '{address}': {e}")
        return None, None

def get_traffic_data(lat, lon):
    """Ambil data lalu lintas & info jalan dari TomTom API secara lengkap."""
    traffic_url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    road_url = f"https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json"

    try:
        # Request data lalu lintas & nama jalan
        traffic_response = requests.get(traffic_url, params={"point": f"{lat},{lon}", "key": TOMTOM_API_KEY}, timeout=10)
        traffic_response.raise_for_status()
        traffic_data = traffic_response.json()

        road_response = requests.get(road_url, params={"key": TOMTOM_API_KEY}, timeout=10)
        road_response.raise_for_status()
        road_data = road_response.json()

        # Ekstrak informasi utama
        flow = traffic_data.get("flowSegmentData", {})
        road_info = road_data.get("addresses", [{}])[0].get("address", {})

        road_name = road_info.get("streetName", "Unknown Road")
        current_speed = flow.get("currentSpeed", 0)
        free_speed = flow.get("freeFlowSpeed", 1)
        confidence = flow.get("confidence", 0)
        congestion = max(0, min(1, 1 - (current_speed / free_speed))) if free_speed > 0 else 0

        result = {
            "summary": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "latitude": lat,
                "longitude": lon,
                "road_name": road_name,
                "current_speed": current_speed,
                "free_flow_speed": free_speed,
                "congestion_percent": round(congestion * 100, 1),
                "confidence": confidence
            }
        }
        return result

    except Exception as e:
        print(f"[API ERROR] {e}")
        return {"error": True, "message": str(e)}

def broadcast_message(message):
    """Kirim pesan ke semua client."""
    with clients_lock:
        for client in list(clients):
            try:
                sock.sendto(message.encode(), client)
            except Exception as e:
                print(f"[SEND ERROR] Gagal kirim ke {client}: {e}")
                clients.discard(client)

def traffic_updater():
    """Thread yang secara periodik mengambil dan menyebarkan data lalu lintas."""
    while True:
        with location_lock:
            # --- PERUBAHAN 2: Gunakan koordinat dari variabel global ---
            lat, lon = current_location["lat"], current_location["lon"]
        
        traffic = get_traffic_data(lat, lon)

        if "error" not in traffic:
            s = traffic["summary"]
            msg = (
                f"[LALU LINTAS] {s['timestamp']} | "
                f"Lokasi: {s['road_name']} | "
                f"Kecepatan: {s['current_speed']} km/jam | "
                f"Kemacetan: {s['congestion_percent']}% | "
                f"Confidence: {s['confidence']}"
            )
            print(f"[SERVER] Broadcast: {msg}")
            broadcast_message(msg)
        else:
            error_msg = f"[LALU LINTAS] Gagal ambil data: {traffic['message']}"
            print(f"[SERVER] {error_msg}")
            broadcast_message(error_msg)

        time.sleep(UPDATE_INTERVAL)

def handle_client():
    """Thread untuk menerima pesan dari client (JOIN, SEARCH)."""
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode().strip()
            
            with clients_lock:
                # Tambahkan client jika belum ada
                if addr not in clients:
                    clients.add(addr)
                    print(f"[SERVER] Client baru: {addr}")
                    sock.sendto(b"[SERVER] Anda berhasil terhubung! Silakan cari lokasi.", addr)

            # --- PERUBAHAN 3: Logika untuk menangani perintah dari client ---
            if message.upper() == "JOIN":
                # Respon JOIN bisa diabaikan jika sudah ditangani di atas
                pass
            elif message.upper().startswith("SEARCH:"):
                address = message.split(":", 1)[1].strip()
                print(f"[SERVER] Menerima permintaan pencarian untuk: '{address}' dari {addr}")
                
                lat, lon = geocode_address(address)
                
                if lat and lon:
                    with location_lock:
                        current_location["name"] = address
                        current_location["lat"] = lat
                        current_location["lon"] = lon
                    
                    success_msg = f"[SERVER] OK: Lokasi pemantauan diubah ke '{address}'. Update akan dimulai."
                    print(success_msg)
                    broadcast_message(success_msg) # Beri tahu semua client
                else:
                    error_msg = f"[SERVER] GAGAL: Lokasi '{address}' tidak ditemukan."
                    print(error_msg)
                    sock.sendto(error_msg.encode(), addr) # Hanya beri tahu client yang meminta

        except Exception as e:
            print(f"[RECV ERROR] {e}")

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_HOST, SERVER_PORT))
    print(f"[SERVER] Berjalan di {SERVER_HOST}:{SERVER_PORT}")
    print(f"[SERVER] Lokasi default: {current_location['name']}")

    threading.Thread(target=handle_client, daemon=True).start()
    threading.Thread(target=traffic_updater, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SERVER] Dimatikan.")
        sock.close()