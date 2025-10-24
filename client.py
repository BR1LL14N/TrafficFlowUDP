import socket

SERVER_IP = "127.0.0.1"   # Ganti dengan IP publik server jika dari luar
SERVER_PORT = 5000
LOCAL_PORT = 5001

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", LOCAL_PORT))

# Daftar ke server
sock.sendto(b"JOIN", (SERVER_IP, SERVER_PORT))
print("[CLIENT] Terdaftar ke server. Menunggu update cuaca...")

while True:
    data, _ = sock.recvfrom(1024)
    print("📡", data.decode('utf-8'))