import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import re
import os 

# === Konfigurasi Server ===
SERVER_HOST = "192.168.14.67" 
SERVER_PORT = 5005

# === Konfigurasi File Log ===
LOG_FILE = "traffic_monitor_log.txt"
if not os.path.exists(LOG_FILE):
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("--- Log Monitor Lalu Lintas Dimulai ---\n")
    except IOError as e:
        print(f"Peringatan: Gagal membuat file log awal: {e}")


class TrafficMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 Monitor Lalu Lintas Real-Time")
        self.root.geometry("800x650") 
        self.root.resizable(True, True)

        # === Style ===
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Arial", 11))
        style.configure("Bold.TLabel", background="#f0f0f0", font=("Arial", 11, "bold"))
        style.configure("TButton", font=("Arial", 10, "bold"), padding=5)
        style.configure("TLabelframe", background="#f0f0f0", padding=10)
        style.configure("TLabelframe.Label", background="#f0f0f0", font=("Arial", 13, "bold"), foreground="#003366")
        
        # --- PERUBAHAN 1: Tambahkan Style untuk Tombol Reset (Merah) ---
        style.configure("Danger.TButton", font=("Arial", 10, "bold"), padding=5, background="#dc3545", foreground="white")
        # Efek hover/active
        style.map("Danger.TButton",
            background=[('active', '#c82333')],
            foreground=[('active', 'white')]
        )
        
        self.root.configure(background="#f0f0f0")

        # --- Frame untuk Input Lokasi ---
        search_frame = ttk.Frame(root, padding=10, style="TFrame")
        search_frame.pack(fill="x", padx=15, pady=10)
        
        ttk.Label(search_frame, text="🔍 Cari Nama Jalan:", style="Bold.TLabel").pack(side="left", padx=(0, 10))
        
        self.address_entry = ttk.Entry(search_frame, font=("Arial", 11), width=40)
        self.address_entry.pack(side="left", fill="x", expand=True)
        self.address_entry.bind("<Return>", self.request_new_location)
        
        self.search_button = ttk.Button(search_frame, text="Cari Lokasi", command=self.request_new_location)
        self.search_button.pack(side="left", padx=(10, 0))
        
        # --- PERUBAHAN 2: Tambahkan Tombol Reset ---
        self.reset_button = ttk.Button(search_frame, text="Reset", command=self.request_reset, style="Danger.TButton")
        self.reset_button.pack(side="left", padx=(5, 0))
        
        
        # --- LabelFrame untuk Data Real-Time ---
        realtime_labelframe = ttk.LabelFrame(root, text="ℹ️ Data Real-Time", style="TLabelframe")
        realtime_labelframe.pack(fill="x", padx=20, pady=5)

        info_frame = ttk.Frame(realtime_labelframe, style="TFrame", padding=5)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_frame.columnconfigure(0, weight=1) 
        info_frame.columnconfigure(1, weight=3) 

        self.location_var = tk.StringVar(value="—")
        self.speed_var = tk.StringVar(value="—")
        self.congestion_var = tk.StringVar(value="—")
        self.confidence_var = tk.StringVar(value="—")
        self.timestamp_var = tk.StringVar(value="—")

        # Baris 0: Lokasi
        ttk.Label(info_frame, text="Lokasi:", style="Bold.TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(info_frame, textvariable=self.location_var, font=("Arial", 11), wraplength=450).grid(row=0, column=1, sticky="w", padx=10, pady=3)

        # Baris 1: Kecepatan
        ttk.Label(info_frame, text="Kecepatan:", style="Bold.TLabel").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(info_frame, textvariable=self.speed_var, font=("Arial", 11)).grid(row=1, column=1, sticky="w", padx=10, pady=3)

        # Baris 2: Kemacetan
        ttk.Label(info_frame, text="Kemacetan:", style="Bold.TLabel").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        # Simpan style default untuk reset
        self.default_label_bg = style.lookup("TLabel", "background")
        self.default_label_fg = style.lookup("TLabel", "foreground")
        self.default_label_font = style.lookup("TLabel", "font")

        self.congestion_label = ttk.Label(info_frame, textvariable=self.congestion_var, font=self.default_label_font, padding=(8, 3))
        self.congestion_label.grid(row=2, column=1, sticky="w", padx=10, pady=3)


        # Baris 3: Confidence
        ttk.Label(info_frame, text="Confidence:", style="Bold.TLabel").grid(row=3, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(info_frame, textvariable=self.confidence_var, font=("Arial", 11)).grid(row=3, column=1, sticky="w", padx=10, pady=3)

        # Baris 4: Waktu Update
        ttk.Label(info_frame, text="Waktu Update:", style="Bold.TLabel").grid(row=4, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(info_frame, textvariable=self.timestamp_var, font=("Arial", 11)).grid(row=4, column=1, sticky="w", padx=10, pady=3)
        
        # --- LabelFrame untuk Log ---
        log_labelframe = ttk.LabelFrame(root, text="📜 Riwayat & Log Server", style="TLabelframe")
        log_labelframe.pack(fill="both", expand=True, padx=20, pady=(10, 20)) 

        self.log_text = scrolledtext.ScrolledText(log_labelframe, wrap=tk.WORD, height=15, font=("Consolas", 10), relief=tk.FLAT)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED, background="#ffffff") 

        # Buat socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.sendto(b"JOIN", (SERVER_HOST, SERVER_PORT))
        except Exception as e:
            messagebox.showerror("Koneksi Gagal", f"Tidak dapat terhubung ke server di {SERVER_HOST}:{SERVER_PORT}\nError: {e}")
            self.root.destroy()
            return
            
        threading.Thread(target=self.receive_messages, daemon=True).start()

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
            self.address_entry.delete(0, tk.END) 
        except Exception as e:
            error_msg = f"Gagal mengirim permintaan: {e}"
            messagebox.showerror("Koneksi Error", error_msg)
            self.add_log(f"[CLIENT] ERROR: {error_msg}")

    # --- PERUBAHAN 3: Fungsi baru untuk mengirim RESET ---
    def request_reset(self):
        """Kirim perintah RESET ke server."""
        # Tampilkan konfirmasi
        if messagebox.askyesno("Konfirmasi Reset", "Anda yakin ingin menghentikan pemantauan di semua client?"):
            try:
                self.sock.sendto(b"RESET", (SERVER_HOST, SERVER_PORT))
                self.add_log("[CLIENT] Meminta reset pemantauan.")
            except Exception as e:
                error_msg = f"Gagal mengirim permintaan reset: {e}"
                messagebox.showerror("Koneksi Error", error_msg)
                self.add_log(f"[CLIENT] ERROR: {error_msg}")

    # --- PERUBAHAN 4: Fungsi baru untuk membersihkan display ---
    def clear_display(self):
        """Mengembalikan tampilan GUI ke status awal '—'."""
        self.location_var.set("—")
        self.speed_var.set("—")
        self.congestion_var.set("—")
        # Kembalikan style label kemacetan ke default
        self.congestion_label.config(
            background=self.default_label_bg, 
            foreground=self.default_label_fg, 
            font=self.default_label_font
        )
        self.confidence_var.set("—")
        self.timestamp_var.set("—")


    def update_display(self, data_dict):
        """Update tampilan GUI dengan data terbaru."""
        self.location_var.set(data_dict.get("lokasi", "—"))
        self.speed_var.set(f"{data_dict.get('kecepatan', 0)} km/jam")
        congestion = data_dict.get("kemacetan", 0)
        self.congestion_var.set(f"{congestion}%")
        
        font_style = ("Arial", 11, "bold") 
        if congestion < 30:
            color, fg = "#d4edda", "#155724" # Hijau
        elif congestion < 70:
            color, fg = "#fff3cd", "#856404" # Kuning
        else:
            color, fg = "#f8d7da", "#721c24" # Merah
        
        self.congestion_label.config(background=color, foreground=fg, font=font_style)
        self.confidence_var.set(f"{data_dict.get('confidence', 0):.4f}")
        self.timestamp_var.set(data_dict.get("waktu", "—"))

    def add_log(self, raw_message):
        """Tambahkan pesan ke GUI log DAN simpan ke file."""
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"{raw_message}\n")
            self.log_text.yview(tk.END) 
            self.log_text.config(state=tk.DISABLED)
        except tk.TclError as e:
            print(f"Error updating GUI log: {e}")

        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{raw_message}\n")
        except IOError as e:
            print(f"ERROR: Gagal menyimpan log ke {LOG_FILE}: {e}")

    def parse_message(self, message):
        """Parsing pesan data lalu lintas (Regex)."""
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
                data, _ = self.sock.recvfrom(2048)
                raw_msg = data.decode("utf-8", errors="replace").strip()
                self.root.after(0, self.handle_received_message, raw_msg)
            except Exception as e:
                if self.sock._closed:
                    print("[CLIENT] Socket ditutup, thread penerima berhenti.")
                    break
                print(f"[GUI ERROR] {e}")
                self.root.after(0, self.add_log, f"Koneksi terputus: {e}")
                break

    # --- PERUBAHAN 5: Modifikasi handler untuk mengenali pesan RESET ---
    def handle_received_message(self, raw_msg):
        """Fungsi yang dipanggil di main thread untuk memproses pesan."""
        self.add_log(raw_msg)
        
        if raw_msg.startswith("[LALU LINTAS]"):
            parsed = self.parse_message(raw_msg)
            if parsed:
                self.update_display(parsed)
        
        # Cek apakah ini pesan konfirmasi reset atau standby dari server
        elif "Pemantauan dihentikan" in raw_msg or "mode standby" in raw_msg:
            # Jika server konfirmasi reset, bersihkan GUI
            self.clear_display()


    def on_closing(self):
        """Handler saat jendela ditutup."""
        print("[CLIENT] Menutup aplikasi...")
        self.sock.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TrafficMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()