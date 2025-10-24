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
UPDATE_INTERVAL = 10  # detik

# Simpan client aktif: set dari (ip, port)
clients = set()
clients_lock = threading.Lock()

def get_traffic_data(lat, lon):
    """Ambil data lalu lintas dari TomTom API."""
    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    try:
        response = requests.get(url, params={"point": f"{lat},{lon}", "key": TOMTOM_API_KEY}, timeout=10)
        response.raise_for_status()
        data = response.json()
        flow = data.get("flowSegmentData", {})
        current = flow.get("currentSpeed", 0)
        free = flow.get("freeFlowSpeed", 1)
        congestion = max(0, min(1, 1 - (current / free))) if free > 0 else 0
        return {
            "road": flow.get("roadName", "Unknown"),
            "current_speed": current,
            "free_flow_speed": free,
            "congestion_percent": round(congestion * 100, 1),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        print(f"[API ERROR] {e}")
        return None

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
    # Koordinat Jalan Kenjeran, Surabaya (dekat Kenjeran Park)
    LAT = -7.245894285857918
    LON = 112.77131218188374
    while True:
        traffic = get_traffic_data(LAT, LON)
        if traffic:
            msg = (
                f"[LALU LINTAS KENJERAN] {traffic['timestamp']} | "
                f"Jalan: {traffic['road']} | "
                f"Kecepatan: {traffic['current_speed']} km/jam | "
                f"Kemacetan: {traffic['congestion_percent']}%"
            )
            print(f"[SERVER] Broadcast: {msg}")
            broadcast_message(msg)
        else:
            error_msg = "[LALU LINTAS] Gagal ambil data untuk Kenjeran"
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