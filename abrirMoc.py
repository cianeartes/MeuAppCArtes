import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import json

# --- Configuration & Aesthetics ---
CONFIG_FILE = "config.json"

COLORS = {
    "bg": ("#f1f5f9", "#0f172a"),
    "card": ("#ffffff", "#1e293b"),
    "primary": "#3b82f6",
    "success": "#10b981",
    "text_main": ("#1e293b", "#f1f5f9"),
    "text_dim": ("#64748b", "#94a3b8"),
    "border": ("#e2e8f0", "#334155")
}

VALID_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except:
        pass

class SubfolderRow(ctk.CTkFrame):
    def __init__(self, parent, folder_path, **kwargs):
        super().__init__(parent, fg_color=COLORS["card"], border_width=1, border_color=COLORS["border"], **kwargs)
        self.folder_path = folder_path
        self.folder_name = os.path.basename(folder_path)
        
        self.grid_columnconfigure(1, weight=1)
        self.configure(height=120)

        # Folder Info
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.name_label = ctk.CTkLabel(self.info_frame, text=self.folder_name, font=("Segoe UI", 14, "bold"), text_color=COLORS["text_main"])
        self.name_label.pack(anchor="w")
        
        self.path_label = ctk.CTkLabel(self.info_frame, text=self.folder_path, font=("Segoe UI", 10), text_color=COLORS["text_dim"])
        self.path_label.pack(anchor="w")

        # Previews Container
        self.previews_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.previews_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Counter and Open Button
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(row=0, column=2, padx=15, pady=10, sticky="e")
        
        self.counter_label = ctk.CTkLabel(self.actions_frame, text="Calculando...", font=("Segoe UI", 12, "bold"), text_color=COLORS["success"])
        self.counter_label.pack(side="left", padx=10)
        
        self.open_btn = ctk.CTkButton(self.actions_frame, text="📁 Abrir", width=80, height=32, 
                                       fg_color=COLORS["primary"], hover_color="#2563eb", 
                                       font=("Segoe UI", 12, "bold"), command=self.open_folder)
        self.open_btn.pack(side="left", padx=5)

        # Load images in background
        threading.Thread(target=self.load_data, daemon=True).start()

    def load_data(self):
        images = []
        total_count = 0
        
        try:
            for root, dirs, files in os.walk(self.folder_path):
                for file in files:
                    if file.lower().endswith(VALID_EXTENSIONS):
                        full_path = os.path.join(root, file)
                        if len(images) < 3:
                            images.append(full_path)
                        total_count += 1
        except:
            pass
        
        self.after(0, lambda: self.update_ui(images, total_count))

    def update_ui(self, images, total_count):
        self.counter_label.configure(text=f"{total_count} imagens")
        
        if not images:
            ctk.CTkLabel(self.previews_frame, text="Sem imagens", font=("Segoe UI", 10, "italic"), text_color=COLORS["text_dim"]).pack(side="left", padx=5)
            return

        for i, img_path in enumerate(images):
            try:
                img = Image.open(img_path)
                img.thumbnail((80, 80))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
                
                lbl = ctk.CTkLabel(self.previews_frame, image=ctk_img, text="", corner_radius=8)
                lbl.pack(side="left", padx=5)
                lbl.image = ctk_img
            except:
                pass

    def open_folder(self):
        if os.path.exists(self.folder_path):
            os.startfile(self.folder_path)
        else:
            messagebox.showerror("Erro", "Pasta não encontrada!")

class AbrirMocApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.config = load_config()
        self.title("Visualizador de Mockups Premium")
        
        # Geometry Persistence
        geo = self.config.get("window_geometry_moc", "1100x750+100+100")
        try:
            self.geometry(geo)
        except:
            self.geometry("1100x750")
            
        # Initial Theme
        theme = self.config.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        
        self.configure(fg_color=COLORS["bg"])
        
        self.setup_ui()
        
        # Auto-load from config
        default_path = self.config.get("mockup_base_path")
        if default_path and os.path.exists(default_path):
            self.path_var.set(default_path)
            self.load_subfolders(default_path)
            
        # Bindings for persistence
        self.bind("<Configure>", self.save_window_geometry)

    def save_window_geometry(self, event=None):
        # Debounced save to avoid excessive disk I/O
        if hasattr(self, "_save_geo_id"):
            self.after_cancel(self._save_geo_id)
        self._save_geo_id = self.after(1000, self._perform_geo_save)

    def _perform_geo_save(self):
        self.config["window_geometry_moc"] = self.geometry()
        save_config(self.config)

    def setup_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, height=140, corner_radius=0, fg_color=COLORS["card"])
        self.header.pack(fill="x", side="top")
        
        # Theme Toggle Button (Top Right)
        self.theme_btn = ctk.CTkButton(self.header, text="🌓", width=40, height=40, corner_radius=20, 
                                        fg_color=COLORS["border"], hover_color=COLORS["primary"], 
                                        text_color=COLORS["text_main"], font=("Segoe UI", 16),
                                        command=self.toggle_theme)
        self.theme_btn.place(relx=0.97, rely=0.25, anchor="ne")

        title_lbl = ctk.CTkLabel(self.header, text="MOCKUP EXPLORER", font=("Segoe UI", 28, "bold"), text_color=COLORS["success"])
        title_lbl.pack(pady=(20, 5))
        
        subtitle_lbl = ctk.CTkLabel(self.header, text="Ciane Artes - Gerenciador de Previsualização", font=("Segoe UI", 11, "bold"), text_color=COLORS["text_dim"])
        subtitle_lbl.pack(pady=(0, 5))
        
        # Sort Row
        self.filter_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.filter_frame.pack(fill="x", padx=30, pady=(0, 15))
        
        self.sort_var = ctk.BooleanVar(value=False)
        self.sort_btn = ctk.CTkCheckBox(self.filter_frame, text="Ordenar por quantidade: Mais imagens primeiro", variable=self.sort_var, 
                                        font=("Segoe UI", 12, "bold"), text_color=COLORS["text_main"],
                                        command=self.on_sort_toggle)
        self.sort_btn.pack(side="left", padx=10)
        

        # Toolbar (Path)
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar.pack(fill="x", padx=30, pady=15)
        
        self.path_var = ctk.StringVar()
        self.path_entry = ctk.CTkEntry(self.toolbar, textvariable=self.path_var, placeholder_text="Selecione a pasta mãe dos seus mockups...", 
                                        height=45, border_color=COLORS["border"], font=("Segoe UI", 13),
                                        fg_color=COLORS["card"], text_color=COLORS["text_main"])
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        self.browse_btn = ctk.CTkButton(self.toolbar, text="📁 Selecionar Pasta", width=180, height=45, 
                                         fg_color=COLORS["primary"], hover_color="#2563eb", 
                                         font=("Segoe UI", 13, "bold"), command=self.browse_folder)
        self.browse_btn.pack(side="left")

        # Scrollable area
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=10)

        # Storage for loaded data to allow quick sorting
        self.all_subdirs_data = []

    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_theme = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new_theme)
        
        # Save to config
        self.config["theme"] = new_theme.lower()
        save_config(self.config)

    def on_sort_toggle(self):
        if not self.path_var.get(): return
        self.load_subfolders(self.path_var.get())

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            self.config["mockup_base_path"] = folder
            save_config(self.config)
            self.load_subfolders(folder)

    def load_subfolders(self, base_folder):
        # Clear current list
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        loading_lbl = ctk.CTkLabel(self.scroll_frame, text="Escaneando pastas e contando imagens... Aguarde.", 
                                   font=("Segoe UI", 14, "italic"), text_color=COLORS["primary"])
        loading_lbl.pack(pady=50)
        self.update()

        def scan_task():
            try:
                subdirs = [os.path.join(base_folder, d) for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d))]
                
                data_list = []
                for subdir in subdirs:
                    # Quick count for sorting
                    count = 0
                    try:
                        for root, dirs, files in os.walk(subdir):
                            for file in files:
                                if file.lower().endswith(VALID_EXTENSIONS):
                                    count += 1
                    except: pass
                    data_list.append({'path': subdir, 'count': count})

                # Sort if requested
                if self.sort_var.get():
                    data_list.sort(key=lambda x: x['count'], reverse=True)
                else:
                    data_list.sort(key=lambda x: os.path.basename(x['path']).lower())

                self.all_subdirs_data = data_list
                self.after(0, self.refresh_ui_list)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro", f"Erro ao listar pastas: {e}"))

        threading.Thread(target=scan_task, daemon=True).start()

    def refresh_ui_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.all_subdirs_data:
            ctk.CTkLabel(self.scroll_frame, text="Diretório vazio ou sem subpastas.", 
                         font=("Segoe UI", 16, "italic"), text_color=COLORS["text_dim"]).pack(pady=50)
            return
            
        for item in self.all_subdirs_data:
            row = SubfolderRow(self.scroll_frame, item['path'])
            row.pack(fill="x", pady=8)

if __name__ == "__main__":
    # DPI Awareness for Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = AbrirMocApp()
    app.mainloop()
