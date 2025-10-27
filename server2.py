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
SERVER_HOST = "0.0.0.0"  # Dengarkan semua antarmuka
SERVER_PORT = 5005
UPDATE_INTERVAL = 3.5  # detik

# Simpan client aktif: set dari (ip, port)
clients = set()
clients_lock = threading.Lock()

def get_traffic_data(lat, lon):
    """Ambil data lalu lintas & info jalan dari TomTom API secara lengkap."""
    traffic_url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    road_url = f"https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json"

    try:
        # ==== 1️⃣ Request data lalu lintas ====
        response = requests.get(traffic_url, params={
            "point": f"{lat},{lon}",
            "key": TOMTOM_API_KEY
        }, timeout=10)
        response.raise_for_status()
        traffic_data = response.json()

        # ==== 2️⃣ Request data nama jalan ====
        response2 = requests.get(road_url, params={"key": TOMTOM_API_KEY}, timeout=10)
        response2.raise_for_status()
        road_data = response2.json()

        # ==== 3️⃣ Ekstrak informasi utama ====
        flow = traffic_data.get("flowSegmentData", {})
        road_info = road_data.get("addresses", [{}])[0].get("address", {})

        road_name = road_info.get("streetName", "Unknown")
        current_speed = flow.get("currentSpeed", 0)
        free_speed = flow.get("freeFlowSpeed", 1)
        confidence = flow.get("confidence", 0)
        congestion = max(0, min(1, 1 - (current_speed / free_speed))) if free_speed > 0 else 0

        # ==== 4️⃣ Gabungkan hasil ====
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
            },
            "reverse_geocoding": road_data,   # response lengkap
            "traffic_flow": traffic_data       # response lengkap
        }

        return result

    except Exception as e:
        print(f"[API ERROR] {e}")
        return {
            "error": True,
            "message": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

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
    #jl wonokromo
    # LAT = -7.302352137612897
    # LON = 112.73684452653953

    #jl ahmad yani
    # LAT = -7.385263061710606
    # LON = 112.72859890463283

    #Jalan Prabu Siliwangi
    # LAT = -7.30841281142686 
    # LON = 112.71237302449151 
    # , 
    LAT = -7.327433511958167 
    LON = 112.73226468935879
    while True:
        traffic = get_traffic_data(LAT, LON)

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
    """Thread untuk menerima pesan dari client (JOIN, dll)."""
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode().strip().upper()
            with clients_lock:
                if message == "JOIN":
                    if addr not in clients:
                        clients.add(addr)
                        print(f"[SERVER] Client baru: {addr}")
                        sock.sendto(b"[SERVER] Anda berhasil JOIN! Menunggu update lalu lintas...", addr)
                # Bisa tambahkan perintah lain di sini (misal: QUIT, STATUS, dll)
        except Exception as e:
            print(f"[RECV ERROR] {e}")

if __name__ == "__main__":
    # Buat socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_HOST, SERVER_PORT))
    print(f"[SERVER] Berjalan di {SERVER_HOST}:{SERVER_PORT}")
    print("[SERVER] Menunggu client...")

    # Jalankan thread
    threading.Thread(target=handle_client, daemon=True).start()
    threading.Thread(target=traffic_updater, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SERVER] Dimatikan.")
        sock.close()