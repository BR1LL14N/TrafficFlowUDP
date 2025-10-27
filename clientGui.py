# client_gui.py
import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import re

# === Konfigurasi Server ===
SERVER_HOST = "192.168.14.67"  # Ganti sesuai IP server Anda
SERVER_PORT = 5005

class TrafficMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 Monitor Lalu Lintas Real-Time")
        self.root.geometry("750x600")
        self.root.resizable(True, True)

        # Style
        style = ttk.Style()
        style.theme_use("clam")

        # --- PERUBAHAN 1: Tambah Frame untuk Input Lokasi ---
        search_frame = ttk.Frame(root, padding=10)
        search_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(search_frame, text="🔍 Cari Nama Jalan:", font=("Arial", 11, "bold")).pack(side="left", padx=(0, 10))
        
        self.address_entry = ttk.Entry(search_frame, font=("Arial", 11), width=40)
        self.address_entry.pack(side="left", fill="x", expand=True)
        self.address_entry.bind("<Return>", self.request_new_location) # Kirim saat menekan Enter
        
        self.search_button = ttk.Button(search_frame, text="Cari Lokasi", command=self.request_new_location)
        self.search_button.pack(side="left", padx=(10, 0))
        
        # Header
        header = tk.Label(root, text="📊 Update Lalu Lintas Real-Time", font=("Arial", 16, "bold"))
        header.pack()

        # Info Panel (Terbaru)
        info_frame = ttk.Frame(root, padding=10)
        info_frame.pack(fill="x", padx=20, pady=5)
        
        self.location_var = tk.StringVar(value="—")
        # ... (sisa variabel sama)
        self.speed_var = tk.StringVar(value="—")
        self.congestion_var = tk.StringVar(value="—")
        self.confidence_var = tk.StringVar(value="—")
        self.timestamp_var = tk.StringVar(value="—")

        ttk.Label(info_frame, text="Lokasi:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.location_var, font=("Arial", 10)).grid(row=0, column=1, sticky="w", padx=10)

        ttk.Label(info_frame, text="Kecepatan:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.speed_var, font=("Arial", 10)).grid(row=1, column=1, sticky="w", padx=10)

        ttk.Label(info_frame, text="Kemacetan:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5)
        self.congestion_label = ttk.Label(info_frame, textvariable=self.congestion_var, font=("Arial", 10), padding=(5,2))
        self.congestion_label.grid(row=2, column=1, sticky="w", padx=10)

        ttk.Label(info_frame, text="Confidence:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.confidence_var, font=("Arial", 10)).grid(row=3, column=1, sticky="w", padx=10)

        ttk.Label(info_frame, text="Waktu Update:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.timestamp_var, font=("Arial", 10)).grid(row=4, column=1, sticky="w", padx=10)

        # Separator
        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10)
        
        # Log Riwayat
        log_label = tk.Label(root, text="📜 Riwayat Update & Log Server", font=("Arial", 12, "underline"))
        log_label.pack(pady=(0, 5))

        self.log_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=12, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.log_text.config(state=tk.DISABLED)

        # Buat socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Kirim JOIN ke server untuk mendaftarkan diri
        self.sock.sendto(b"JOIN", (SERVER_HOST, SERVER_PORT))
        
        # Mulai thread penerima
        threading.Thread(target=self.receive_messages, daemon=True).start()

    # --- PERUBAHAN 2: Fungsi Baru untuk Mengirim Permintaan Lokasi ---
    def request_new_location(self, event=None):
        """Ambil teks dari entry dan kirim ke server."""
        address = self.address_entry.get().strip()
        if not address:
            messagebox.showwarning("Input Kosong", "Silakan masukkan nama jalan atau lokasi.")
            return

        message = f"SEARCH:{address}"
        try:
            self.sock.sendto(message.encode(), (SERVER_HOST, SERVER_PORT))
            self.add_log(f"[CLIENT] Meminta lokasi baru: '{address}'")
            self.address_entry.delete(0, tk.END) # Kosongkan input setelah dikirim
        except Exception as e:
            error_msg = f"Gagal mengirim permintaan: {e}"
            messagebox.showerror("Koneksi Error", error_msg)
            self.add_log(f"[CLIENT] ERROR: {error_msg}")

    def update_display(self, data_dict):
        """Update tampilan GUI dengan data terbaru."""
        # ... (Fungsi ini tidak berubah)
        self.location_var.set(data_dict.get("lokasi", "—"))
        self.speed_var.set(f"{data_dict.get('kecepatan', 0)} km/jam")
        congestion = data_dict.get("kemacetan", 0)
        self.congestion_var.set(f"{congestion}%")
        
        if congestion < 30:
            color, fg = "#d4edda", "#155724" # Hijau
        elif congestion < 70:
            color, fg = "#fff3cd", "#856404" # Kuning
        else:
            color, fg = "#f8d7da", "#721c24" # Merah
        
        self.congestion_label.config(background=color, foreground=fg)
        self.confidence_var.set(f"{data_dict.get('confidence', 0):.4f}")
        self.timestamp_var.set(data_dict.get("waktu", "—"))

    def add_log(self, raw_message):
        # ... (Fungsi ini tidak berubah)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{raw_message}\n")
        self.log_text.yview(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def parse_message(self, message):
        # ... (Fungsi ini tidak berubah)
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
                data, _ = self.sock.recvfrom(2048) # buffer diperbesar sedikit
                raw_msg = data.decode("utf-8", errors="replace").strip()
                
                # Update GUI di thread utama untuk menghindari error Tkinter
                self.root.after(0, self.handle_received_message, raw_msg)

            except Exception as e:
                print(f"[GUI ERROR] {e}")
                self.root.after(0, self.add_log, f"Koneksi terputus: {e}")
                break

    def handle_received_message(self, raw_msg):
        """Fungsi yang dipanggil di main thread untuk memproses pesan."""
        self.add_log(raw_msg)
        
        # Coba parse jika ini pesan data lalu lintas
        if raw_msg.startswith("[LALU LINTAS]"):
            parsed = self.parse_message(raw_msg)
            if parsed:
                self.update_display(parsed)

if __name__ == "__main__":
    root = tk.Tk()
    app = TrafficMonitorApp(root)
    root.mainloop()