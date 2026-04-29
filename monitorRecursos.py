import os
import sys
import time
import threading
import psutil
import customtkinter as ctk
import ctypes
from tkinter import messagebox, Menu
import pystray
from PIL import Image, ImageDraw
import json

# --- Configuration & Aesthetics ---
COLORS = {
    "bg": "#0f172a",
    "card": "#1e293b",
    "primary": "#3b82f6",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "text": "#f1f5f9",
    "text_dim": "#94a3b8"
}

def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except: pass
    return {}

def save_config(config):
    config_path = "config.json"
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
    except: pass

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ResourceMonitor(ctk.CTkToplevel):
    def __init__(self):
        # Root invisível para esconder da barra de tarefas
        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        
        super().__init__(master=self.root)

        # Garantir invisibilidade na barra de tarefas (Windows)
        if sys.platform == "win32":
            self.attributes("-toolwindow", True)

        self.config = load_config()
        self.visibility = self.config.get("visibility", {"CPU": True, "RAM": True, "Network": True, "Disks": True})
        self.selected_disks = self.config.get("selected_disks", self.get_initial_disks())
        self.hide_main_bg = self.config.get("hide_main_bg", False)
        
        # Configurar Janela
        self.title("Monitor de Recursos")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        
        # Restaurar Geometria
        geo = self.config.get("monitor_geometry", "280x400+100+100")
        try: self.geometry(geo)
        except: self.geometry("280x400+100+100")

        self.attributes("-alpha", self.config.get("monitor_alpha", 0.95))
        self.key_color = "#000001"
        
        # Ícone da Janela
        self.icon_path = resource_path("monitoramento.ico")
        if os.path.exists(self.icon_path):
            self.after(200, lambda: self.iconbitmap(self.icon_path))

        self.setup_ui()
        self.setup_tray()
        
        if self.hide_main_bg:
            self.after(500, self.apply_hide_main_bg)
        else:
            self.configure(fg_color=COLORS["bg"])

        # Monitoramento
        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_time = time.time()
        
        # Binds
        self.bind("<Button-3>", self.show_context_menu)
        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)
        self.title_lbl.bind("<Button-1>", self.start_move)
        self.title_lbl.bind("<B1-Motion>", self.do_move)

        self.running = True
        threading.Thread(target=self.refresh_stats, daemon=True).start()

    def get_initial_disks(self):
        disks = []
        for part in psutil.disk_partitions():
            if 'fixed' in part.opts:
                try:
                    psutil.disk_usage(part.mountpoint)
                    disks.append(part.mountpoint)
                except: continue
        return disks[:1]

    def setup_ui(self):
        # Header (Barra de Opções)
        self.header = ctk.CTkFrame(self, height=35, corner_radius=0, fg_color=COLORS["card"])
        self.header.pack(fill="x", side="top")
        
        self.title_lbl = ctk.CTkLabel(self.header, text="💻 MONITOR", font=("Segoe UI", 11, "bold"), text_color=COLORS["primary"])
        self.title_lbl.pack(side="left", padx=15)

        self.close_btn = ctk.CTkButton(self.header, text="✕", width=30, height=30, fg_color="transparent", 
                                        hover_color=COLORS["danger"], command=self.withdraw)
        self.close_btn.pack(side="right", padx=5)
        
        self.min_btn = ctk.CTkButton(self.header, text="—", width=30, height=30, fg_color="transparent", 
                                       hover_color=COLORS["primary"], command=self.withdraw)
        self.min_btn.pack(side="right", padx=2)
        
        self.settings_btn = ctk.CTkButton(self.header, text="⚙", width=30, height=30, fg_color="transparent", 
                                           hover_color=COLORS["primary"], command=lambda: self.show_context_menu(None))
        self.settings_btn.pack(side="right", padx=2)

        # Content
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=8, pady=8)
        
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)

        self.widgets = {}
        self.rebuild_ui()

        # Grip
        self.resize_grip = ctk.CTkLabel(self, text="◢", font=("Arial", 10), text_color=COLORS["text_dim"], cursor="size_nw_se")
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se")
        self.resize_grip.bind("<Button-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.do_resize)

    def rebuild_ui(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        self.widgets = {}
        self.block_bg = COLORS["card"]

        if self.visibility["CPU"]:
            self.widgets["cpu"] = self.create_block("CPU", COLORS["primary"])
        if self.visibility["RAM"]:
            self.widgets["ram"] = self.create_block("RAM", COLORS["success"])
        if self.visibility["Network"]:
            self.widgets["net"] = self.create_net_block()
        if self.visibility["Disks"]:
            self.widgets["disks"] = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            self.widgets["disks"].pack(fill="x", pady=2)
            self.rebuild_disks()

    def create_block(self, title, color):
        frame = ctk.CTkFrame(self.content_frame, fg_color=self.block_bg, corner_radius=6)
        frame.pack(fill="x", pady=2, padx=2)
        
        # Binds para arrastar mesmo sem barra superior
        frame.bind("<Button-1>", self.start_move)
        frame.bind("<B1-Motion>", self.do_move)
        frame.bind("<Button-3>", self.show_context_menu)
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=(4, 0))
        
        l1 = ctk.CTkLabel(inner, text=title, font=("Segoe UI", 9, "bold"), text_color=COLORS["text_dim"])
        l1.pack(side="left")
        
        val_lbl = ctk.CTkLabel(inner, text="--%", font=("Segoe UI", 10, "bold"), text_color=COLORS["text"])
        val_lbl.pack(side="right")
        
        bar = ctk.CTkProgressBar(frame, height=5, fg_color="#334155", progress_color=color)
        bar.pack(fill="x", padx=8, pady=6)
        bar.set(0)
        
        # Vincular eventos a todos os sub-widgets para facilitar o arraste
        for w in [frame, inner, l1, val_lbl, bar]:
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)
            w.bind("<Button-3>", self.show_context_menu)
            
        return {"val_lbl": val_lbl, "bar": bar}

    def create_net_block(self):
        frame = ctk.CTkFrame(self.content_frame, fg_color=self.block_bg, corner_radius=6)
        frame.pack(fill="x", pady=2, padx=2)
        
        l1 = ctk.CTkLabel(frame, text="REDE", font=("Segoe UI", 9, "bold"), text_color=COLORS["text_dim"])
        l1.pack(anchor="w", padx=8, pady=(4, 0))
        
        val_lbl = ctk.CTkLabel(frame, text="⬇ 0 KB/s | ⬆ 0 KB/s", font=("Segoe UI", 10, "bold"), text_color=COLORS["text"])
        val_lbl.pack(fill="x", padx=8, pady=4)
        
        for w in [frame, l1, val_lbl]:
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)
            w.bind("<Button-3>", self.show_context_menu)
            
        return {"val_lbl": val_lbl}

    def rebuild_disks(self):
        self.widgets["disk_items"] = {}
        for d in self.selected_disks:
            f = ctk.CTkFrame(self.widgets["disks"], fg_color=self.block_bg, corner_radius=6); f.pack(fill="x", pady=1)
            lf = ctk.CTkFrame(f, fg_color="transparent"); lf.pack(fill="x", padx=8, pady=(4, 0))
            l1 = ctk.CTkLabel(lf, text=f"DISCO {d}", font=("Segoe UI", 9, "bold"), text_color=COLORS["text_dim"]); l1.pack(side="left")
            vl = ctk.CTkLabel(lf, text="--%", font=("Segoe UI", 9, "bold"), text_color=COLORS["text"]); vl.pack(side="right")
            sl = ctk.CTkLabel(f, text="L: 0 KB/s | E: 0 KB/s", font=("Segoe UI", 10, "bold"), text_color=COLORS["text"])
            sl.pack(fill="x", padx=8, pady=2)
            b = ctk.CTkProgressBar(f, height=4, fg_color="#334155", progress_color=COLORS["warning"]); b.pack(fill="x", padx=8, pady=(2, 6)); b.set(0)
            
            for w in [f, lf, l1, vl, sl, b]:
                w.bind("<Button-1>", self.start_move)
                w.bind("<B1-Motion>", self.do_move)
                w.bind("<Button-3>", self.show_context_menu)
                
            self.widgets["disk_items"][d] = {"val_lbl": vl, "bar": b, "speed_lbl": sl}

    def show_context_menu(self, event):
        menu = Menu(self, tearoff=0, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10))
        
        # Visibilidade
        v_menu = Menu(menu, tearoff=0, bg=COLORS["card"], fg=COLORS["text"])
        for k in self.visibility:
            status = "✓ " if self.visibility[k] else "  "
            v_menu.add_command(label=f"{status}{k}", command=lambda i=k: self.toggle_visibility(i))
        menu.add_cascade(label="Exibir Itens", menu=v_menu)

        # Transparência
        t_menu = Menu(menu, tearoff=0, bg=COLORS["card"], fg=COLORS["text"])
        for v in [0.3, 0.5, 0.7, 0.9, 1.0]:
            label = f"{int(v*100)}%"
            status = "✓ " if abs(self.attributes("-alpha") - v) < 0.01 else "  "
            t_menu.add_command(label=f"{status}{label}", command=lambda val=v: self.set_alpha(val))
        menu.add_cascade(label="Transparência Geral", menu=t_menu)

        # Ocultar Fundo Principal
        h_status = "✓ " if self.hide_main_bg else "  "
        menu.add_command(label=f"{h_status}Ocultar Fundo Principal", command=self.toggle_hide_main_bg)

        # Seleção de Discos
        d_menu = Menu(menu, tearoff=0, bg=COLORS["card"], fg=COLORS["text"])
        all_p = [p.mountpoint for p in psutil.disk_partitions() if 'fixed' in p.opts]
        for p in all_p:
            status = "✓ " if p in self.selected_disks else "  "
            d_menu.add_command(label=f"{status}Unidade {p}", command=lambda unit=p: self.toggle_disk(unit))
        menu.add_cascade(label="Selecionar Discos", menu=d_menu)

        menu.add_separator()
        menu.add_command(label="Fechar", command=self.exit_app)
        
        if event: menu.post(event.x_root, event.y_root)
        else: menu.post(self.settings_btn.winfo_rootx(), self.settings_btn.winfo_rooty() + 30)

    def toggle_visibility(self, item):
        self.visibility[item] = not self.visibility[item]
        self.rebuild_ui(); self.save_state()

    def set_alpha(self, val):
        self.attributes("-alpha", val); self.save_state()

    def toggle_hide_main_bg(self):
        self.hide_main_bg = not self.hide_main_bg
        self.apply_hide_main_bg()
        self.save_state()

    def apply_hide_main_bg(self):
        if self.hide_main_bg:
            self.attributes("-transparentcolor", self.key_color)
            self.configure(fg_color=self.key_color)
            self.header.pack_forget()
        else:
            self.attributes("-transparentcolor", "")
            self.configure(fg_color=COLORS["bg"])
            self.header.pack(fill="x", side="top", before=self.main_container)
        self.rebuild_ui()

    def toggle_disk(self, unit):
        if unit in self.selected_disks:
            if len(self.selected_disks) > 1:
                self.selected_disks.remove(unit)
        else:
            self.selected_disks.append(unit)
        self.rebuild_ui()
        self.save_state()

    def start_move(self, event):
        self.move_x, self.move_y = event.x, event.y
    def do_move(self, event):
        nx, ny = self.winfo_x() + (event.x - self.move_x), self.winfo_y() + (event.y - self.move_y)
        self.geometry(f"+{nx}+{ny}"); self.save_state_delayed()

    def start_resize(self, event):
        self.rs_x, self.rs_y, self.rs_w, self.rs_h = event.x_root, event.y_root, self.winfo_width(), self.winfo_height()
    def do_resize(self, event):
        nw, nh = max(150, self.rs_w + (event.x_root - self.rs_x)), max(100, self.rs_h + (event.y_root - self.rs_y))
        self.geometry(f"{nw}x{nh}"); self.save_state_delayed()

    def save_state_delayed(self):
        if hasattr(self, "_save_id"): self.after_cancel(self._save_id)
        self._save_id = self.after(1000, self.save_state)

    def save_state(self):
        config = {
            "monitor_geometry": self.geometry(),
            "monitor_alpha": self.attributes("-alpha"),
            "visibility": self.visibility,
            "hide_main_bg": self.hide_main_bg,
            "selected_disks": self.selected_disks
        }
        save_config(config)

    def refresh_stats(self):
        while self.running:
            try:
                now = time.time(); dt = now - self.last_time
                if dt <= 0: dt = 0.1
                ni = psutil.net_io_counters()
                dn = (ni.bytes_recv - self.last_net_io.bytes_recv) / dt
                up = (ni.bytes_sent - self.last_net_io.bytes_sent) / dt
                self.last_net_io = ni
                di = psutil.disk_io_counters()
                dr = (di.read_bytes - self.last_disk_io.read_bytes) / dt
                dw = (di.write_bytes - self.last_disk_io.write_bytes) / dt
                self.last_disk_io = di; self.last_time = now
                def fmt(s): return f"{s/(1024**2):.1f}MB/s" if s > 1024**2 else f"{s/1024:.1f}KB/s"
                stats = {
                    "cpu": psutil.cpu_percent(), "ram": psutil.virtual_memory().percent,
                    "ram_t": f"{psutil.virtual_memory().percent}% ({psutil.virtual_memory().used/(1024**3):.1f}GB)",
                    "net": f"⬇ {fmt(dn)} | ⬆ {fmt(up)}", "disk_speed": f"L: {fmt(dr)} | E: {fmt(dw)}",
                    "disks": {d: psutil.disk_usage(d).percent for d in self.selected_disks}
                }
                self.after(0, lambda s=stats: self.update_ui(s))
            except: pass
            time.sleep(1)

    def update_ui(self, s):
        if "cpu" in self.widgets: self.widgets["cpu"]["val_lbl"].configure(text=f"{s['cpu']}%"); self.widgets["cpu"]["bar"].set(s['cpu']/100)
        if "ram" in self.widgets: self.widgets["ram"]["val_lbl"].configure(text=s['ram_t']); self.widgets["ram"]["bar"].set(s['ram']/100)
        if "net" in self.widgets: self.widgets["net"]["val_lbl"].configure(text=s['net'])
        if "disk_items" in self.widgets:
            for d, pct in s["disks"].items():
                if d in self.widgets["disk_items"]:
                    self.widgets["disk_items"][d]["val_lbl"].configure(text=f"{pct}%")
                    self.widgets["disk_items"][d]["bar"].set(pct/100)
                    self.widgets["disk_items"][d]["speed_lbl"].configure(text=s["disk_speed"])

    def setup_tray(self):
        icon_path = resource_path("monitoramento.ico")
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
            except:
                img = Image.new('RGB', (64, 64), COLORS["primary"])
                ImageDraw.Draw(img).rectangle((16, 16, 48, 48), fill=COLORS["bg"])
        else:
            img = Image.new('RGB', (64, 64), COLORS["primary"])
            ImageDraw.Draw(img).rectangle((16, 16, 48, 48), fill=COLORS["bg"])
            
        self.tray = pystray.Icon("Monitor", img, "Monitor", menu=pystray.Menu(
            pystray.MenuItem("Exibir/Ocultar", self.toggle_win),
            pystray.MenuItem("Ocultar Fundo Principal", self.toggle_hide_main_bg, checked=lambda item: self.hide_main_bg),
            pystray.MenuItem("Sair", self.exit_app)
        ))
        threading.Thread(target=self.tray.run, daemon=True).start()

    def toggle_win(self):
        if self.winfo_viewable(): self.withdraw()
        else: self.deiconify(); self.attributes("-topmost", True)

    def exit_app(self):
        self.running = False; self.tray.stop(); self.root.destroy(); sys.exit()

if __name__ == "__main__":
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = ResourceMonitor()
    app.root.mainloop()
