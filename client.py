# client.py
import socket
import threading
import sys
import time

SERVER_HOST = "172.18.3.16"  # Ganti dengan IP publik/server Anda saat deploy
SERVER_PORT = 5005

def receive_messages(sock):
    """Terima pesan dari server."""
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            print(data.decode())
        except Exception as e:
            print(f"[ERROR] {e}")
            break

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Kirim JOIN ke server
    sock.sendto(b"JOIN", (SERVER_HOST, SERVER_PORT))
    print("[CLIENT] Mengirim JOIN ke server...")

    # Mulai thread penerima
    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

    try:
        print("[CLIENT] Menunggu pesan dari server. Tekan Ctrl+C untuk keluar.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[CLIENT] Keluar.")
        sock.close()
        sys.exit()