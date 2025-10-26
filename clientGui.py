# client_gui.py
import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import re
from datetime import datetime

# === Konfigurasi Server ===
SERVER_HOST = "192.168.182.227"  # Ganti sesuai IP server Anda
SERVER_PORT = 5005

class TrafficMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 Monitor Lalu Lintas Real-Time")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        # Style
        style = ttk.Style()
        style.theme_use("clam")

        # Header
        header = tk.Label(root, text="📊 Update Lalu Lintas Real-Time", font=("Arial", 16, "bold"), pady=10)
        header.pack()

        # Info Panel (Terbaru)
        info_frame = ttk.Frame(root, padding=10)
        info_frame.pack(fill="x", padx=20, pady=5)

        self.location_var = tk.StringVar(value="—")
        self.speed_var = tk.StringVar(value="—")
        self.congestion_var = tk.StringVar(value="—")
        self.confidence_var = tk.StringVar(value="—")
        self.timestamp_var = tk.StringVar(value="—")

        ttk.Label(info_frame, text="Lokasi:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.location_var, font=("Arial", 10)).grid(row=0, column=1, sticky="w", padx=10)

        ttk.Label(info_frame, text="Kecepatan:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.speed_var, font=("Arial", 10)).grid(row=1, column=1, sticky="w", padx=10)

        ttk.Label(info_frame, text="Kemacetan:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5)
        self.congestion_label = ttk.Label(info_frame, textvariable=self.congestion_var, font=("Arial", 10))
        self.congestion_label.grid(row=2, column=1, sticky="w", padx=10)

        ttk.Label(info_frame, text="Confidence:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.confidence_var, font=("Arial", 10)).grid(row=3, column=1, sticky="w", padx=10)

        ttk.Label(info_frame, text="Waktu Update:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.timestamp_var, font=("Arial", 10)).grid(row=4, column=1, sticky="w", padx=10)

        # Separator
        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10)

        # Log Riwayat
        log_label = tk.Label(root, text="📜 Riwayat Update", font=("Arial", 12, "underline"))
        log_label.pack(pady=(0, 5))

        self.log_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=12, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.log_text.config(state=tk.DISABLED)

        # Kirim JOIN ke server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.sendto(b"JOIN", (SERVER_HOST, SERVER_PORT))
        print("[GUI] Mengirim JOIN ke server...")

        # Mulai thread penerima
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def update_display(self, data_dict):
        """Update tampilan GUI dengan data terbaru."""
        self.location_var.set(data_dict.get("lokasi", "—"))
        self.speed_var.set(f"{data_dict.get('kecepatan', 0)} km/jam")
        congestion = data_dict.get("kemacetan", 0)
        self.congestion_var.set(f"{congestion}%")

        # Ubah warna latar berdasarkan kemacetan
        if congestion < 30:
            color = "#d4edda"  # Hijau muda
            fg = "#155724"
        elif congestion < 70:
            color = "#fff3cd"  # Kuning
            fg = "#856404"
        else:
            color = "#f8d7da"  # Merah muda
            fg = "#721c24"
        self.congestion_label.config(background=color, foreground=fg)

        self.confidence_var.set(f"{data_dict.get('confidence', 0):.4f}")
        self.timestamp_var.set(data_dict.get("waktu", "—"))

    def add_log(self, raw_message):
        """Tambahkan pesan ke riwayat log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, raw_message + "\n")
        self.log_text.yview(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def parse_message(self, message):
        """Parsing pesan dari format teks ke dict."""
        pattern = (
            r"\[LALU LINTAS\] (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| "
            r"Lokasi: ([^|]+) \| "
            r"Kecepatan: (\d+) km/jam \| "
            r"Kemacetan: ([\d.]+)% \| "
            r"Confidence: ([\d.]+)"
        )
        match = re.search(pattern, message)
        if match:
            return {
                "waktu": match.group(1),
                "lokasi": match.group(2).strip(),
                "kecepatan": int(match.group(3)),
                "kemacetan": float(match.group(4)),
                "confidence": float(match.group(5))
            }
        return None

    def receive_messages(self):
        """Thread untuk menerima pesan UDP."""
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
                raw_msg = data.decode("utf-8", errors="replace").strip()
                self.add_log(raw_msg)

                # Coba parse hanya jika bukan pesan error
                if "[LALU LINTAS]" in raw_msg and "Gagal ambil data" not in raw_msg:
                    parsed = self.parse_message(raw_msg)
                    if parsed:
                        # Update GUI di thread utama
                        self.root.after(0, self.update_display, parsed)
            except Exception as e:
                print(f"[GUI ERROR] {e}")
                break

if __name__ == "__main__":
    root = tk.Tk()
    app = TrafficMonitorApp(root)
    root.mainloop()