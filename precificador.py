import os
import json
import csv
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import subprocess
import threading
import math

# --- Configuration & Settings ---
CONFIG_FILE = "config.json"

COLORS = {
    "dark_bg": "#0f172a",
    "dark_card": "#1e293b",
    "light_bg": "#f8fafc",
    "light_card": "#ffffff",
    "primary": "#3b82f6",  # Bright Blue
    "success": "#10b981",  # Emerald Green
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "text_dark": "#f1f5f9",
    "text_light": "#1e293b"
}

DEFAULT_CONFIG = {
    "mockup_base_path": r"C:\ENVIO_PARANUVEM\MOCKUPS",
    "folder_base_path_src": r"C:\ENVIO_PARANUVEM\PASTAS",
    "folder_base_path_dst": [r"C:\ENVIO_PARANUVEM\PASTAS"],
    "theme": "dark",
    "last_csv": "produtos.csv",
    "last_page": 0,
    "window_geometry": "1300x850+100+100",
    "lock_subscription_price": True
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# --- UI Components ---

class TreeModal(ctk.CTkToplevel):
    def __init__(self, parent, title, tree_content):
        super().__init__(parent)
        self.title(f"Descrição - {title}")
        self.geometry("700x600")
        self.attributes("-topmost", True)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkLabel(self, text=f"Estrutura de Pastas: {title}", font=("Segoe UI", 16, "bold"), text_color=COLORS["primary"])
        header.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 11), border_width=2, border_color=COLORS["dark_card"])
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.textbox.insert("0.0", tree_content)
        self.textbox.configure(state="disabled")

class ImageGalleryModal(ctk.CTkToplevel):
    def __init__(self, parent, folder_path, product_name):
        super().__init__(parent)
        self.title(f"Galeria - {product_name}")
        self.geometry("900x800")
        self.attributes("-topmost", True)
        
        self.folder_path = folder_path
        self.images = []
        self.current_idx = 0
        
        if os.path.exists(folder_path):
            valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
            self.image_files = []
            # Limit to 10 images for performance
            for f in os.listdir(folder_path):
                if f.lower().endswith(valid_exts):
                    self.image_files.append(os.path.join(folder_path, f))
                    if len(self.image_files) >= 10:
                        break
        else:
            self.image_files = []
            
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkLabel(self, text=product_name, font=("Segoe UI", 18, "bold"), text_color=COLORS["success"])
        header.grid(row=0, column=0, padx=20, pady=10)
        
        if not self.image_files:
            ctk.CTkLabel(self, text="Nenhuma imagem encontrada na pasta de mockups.", font=("Segoe UI", 14)).grid(row=1, column=0)
            return

        self.canvas_frame = ctk.CTkFrame(self, fg_color="black")
        self.canvas_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        
        self.img_label = ctk.CTkLabel(self.canvas_frame, text="")
        self.img_label.grid(row=0, column=0, sticky="nsew")
        
        self.nav_frame = ctk.CTkFrame(self, height=70, fg_color="transparent")
        self.nav_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        self.prev_btn = ctk.CTkButton(self.nav_frame, text="❮", width=60, height=40, font=("Arial", 20), fg_color=COLORS["primary"], command=self.prev_img)
        self.prev_btn.pack(side="left", padx=10)
        
        self.info_label = ctk.CTkLabel(self.nav_frame, text="", font=("Segoe UI", 14, "bold"))
        self.info_label.pack(side="left", expand=True)
        
        self.next_btn = ctk.CTkButton(self.nav_frame, text="❯", width=60, height=40, font=("Arial", 20), fg_color=COLORS["primary"], command=self.next_img)
        self.next_btn.pack(side="right", padx=10)
        
        # Keyboard bindings for navigation
        self.bind("<Left>", lambda e: self.prev_img())
        self.bind("<Right>", lambda e: self.next_img())
        
        self.show_image()

    def show_image(self):
        img_path = self.image_files[self.current_idx]
        try:
            img = Image.open(img_path)
            # Maintain aspect ratio
            w, h = img.size
            max_w, max_h = 850, 650
            ratio = min(max_w/w, max_h/h)
            new_size = (int(w*ratio), int(h*ratio))
            
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=new_size)
            self.img_label.configure(image=ctk_img, text="")
            self.img_label.image = ctk_img
            
            # Show filename and relative parent folder if any
            filename = os.path.basename(img_path)
            self.info_label.configure(text=f"{self.current_idx + 1} de {len(self.image_files)} | {filename}")
        except Exception as e:
            self.img_label.configure(text=f"Erro ao carregar:\n{e}")

    def next_img(self):
        if self.image_files:
            self.current_idx = (self.current_idx + 1) % len(self.image_files)
            self.show_image()

    def prev_img(self):
        if self.image_files:
            self.current_idx = (self.current_idx - 1) % len(self.image_files)
            self.show_image()

class ProductRow(ctk.CTkFrame):
    def __init__(self, parent, index, data, config, on_save, on_select):
        super().__init__(parent, height=130)
        self.index = index
        self.data = data
        self.config = config
        self.on_save = on_save
        self.on_select = on_select
        
        self.configure(fg_color=(COLORS["light_card"], COLORS["dark_card"]), border_width=1, border_color="#334155")
        
        self.grid_columnconfigure((3, 4), weight=1)
        
        # Selection Checkbox
        self.selected = ctk.BooleanVar(value=False)
        self.check = ctk.CTkCheckBox(self, text="", variable=self.selected, width=24, checkbox_width=24, checkbox_height=24, 
                                     fg_color=COLORS["success"], hover_color=COLORS["primary"], command=self.on_select_internal)
        self.check.grid(row=0, column=0, padx=(15, 5))
        
        self.photo_btn = ctk.CTkButton(self, text="🖼", width=80, height=80, corner_radius=8, 
                                       fg_color="#0f172a", text_color="#64748b", font=("Arial", 24),
                                       command=self.open_gallery)
        self.photo_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # Details Container
        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.details_frame.grid(row=0, column=2, columnspan=4, sticky="nsew", padx=10, pady=10)
        self.details_frame.grid_columnconfigure(1, weight=1)
        
        # ID/Number
        self.num_label = ctk.CTkLabel(self.details_frame, text=f"#{index+1}", width=40, font=("Segoe UI", 12, "bold"), text_color="#94a3b8")
        self.num_label.grid(row=0, column=0, padx=5, sticky="nw")
        
        # Name
        name_val = str(data['Nome Final'])
        self.name_label = ctk.CTkLabel(self.details_frame, text=name_val, anchor="w", font=("Segoe UI", 14, "bold"), 
                                       wraplength=450, justify="left")
        self.name_label.grid(row=0, column=1, padx=5, sticky="w")
        
        # Category
        cat_val = str(data['Categoria']).replace("|", " • ")
        self.cat_label = ctk.CTkLabel(self.details_frame, text=cat_val, anchor="w", font=("Segoe UI", 11), text_color="#64748b")
        self.cat_label.grid(row=1, column=1, padx=5, sticky="w")
        
        # Tipo
        tipo_val = f"Tipo: {data.get('Tipo', 'N/A')}"
        self.tipo_label = ctk.CTkLabel(self.details_frame, text=tipo_val, anchor="w", font=("Segoe UI", 11, "bold"), text_color=COLORS["primary"])
        self.tipo_label.grid(row=2, column=1, padx=5, sticky="w")
        
        # Individual Stats Label
        self.stats_label = ctk.CTkLabel(self.details_frame, text="📊 Calculando...", font=("Segoe UI", 11, "bold"), text_color="#94a3b8")
        self.stats_label.grid(row=3, column=1, padx=5, sticky="w")
        
        # Actions Container
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(row=0, column=5, sticky="ne", padx=15, pady=10)
        
        # Tree Button
        self.tree_btn = ctk.CTkButton(self.actions_frame, text="Tree", width=60, height=28, corner_radius=6,
                                       fg_color="#334155", hover_color="#475569", font=("Segoe UI", 11), command=self.open_tree)
        self.tree_btn.pack(side="left", padx=2)
        
        # Open Folder Button
        self.open_btn = ctk.CTkButton(self.actions_frame, text="Pasta", width=60, height=28, corner_radius=6,
                                       fg_color=COLORS["primary"], hover_color="#2563eb", font=("Segoe UI", 11), command=self.open_folder)
        self.open_btn.pack(side="left", padx=2)

        # Open Mockup Button
        self.mockup_btn = ctk.CTkButton(self.actions_frame, text="Mockup", width=60, height=28, corner_radius=6,
                                         fg_color="#10b981", hover_color="#059669", font=("Segoe UI", 11), command=self.open_mockup_folder)
        self.mockup_btn.pack(side="left", padx=2)

        # Price Entry Frame
        self.price_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.price_frame.grid(row=0, column=6, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.price_frame, text="Preço (R$)", font=("Segoe UI", 10, "bold"), text_color="#94a3b8").pack(pady=(0, 2))
        self.price_var = ctk.StringVar(value=str(data['Preço']))
        self.price_var.trace_add("write", self.sync_price) # Real-time sync
        
        self.price_entry = ctk.CTkEntry(self.price_frame, textvariable=self.price_var, width=100, height=35, 
                                        font=("Segoe UI", 14, "bold"), justify="center", border_color="#475569")
        self.price_entry.pack()
        
        # Lock price if Tipo is ASSINATURA (Optional)
        is_subscription = str(data.get('Tipo', '')).upper() == "ASSINATURA"
        should_lock = self.config.get('lock_subscription_price', True)
        
        if is_subscription and should_lock:
            self.price_entry.configure(state="disabled", fg_color="#334155", text_color="#94a3b8")
        
        # Save Button
        self.save_btn = ctk.CTkButton(self, text="💾", width=50, height=50, corner_radius=25,
                                       fg_color=COLORS["success"], hover_color="#059669", font=("Arial", 20),
                                       command=self.save_item)
        self.save_btn.grid(row=0, column=7, padx=15)
        
        if is_subscription and should_lock:
            self.save_btn.configure(state="disabled", fg_color="#1e293b")
        
        # Load thumbnail in background with a small staggered delay
        self.after(50 + (index % 20) * 10, lambda: threading.Thread(target=self.load_thumbnail, daemon=True).start())

    def on_select_internal(self):
        self.on_select()

    def load_thumbnail(self):
        try:
            mockup_path = os.path.join(self.config['mockup_base_path'], str(self.data['Nome Final']))
            product_path = str(self.data.get('Caminho da Pasta', ''))
            
            valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
            mock_count = 0
            file_count = 0
            first_img = None
            
            # Count Mockups (Recursive)
            if os.path.exists(mockup_path):
                for root, dirs, files in os.walk(mockup_path):
                    for f in files:
                        if f.lower().endswith(valid_exts):
                            full_p = os.path.join(root, f)
                            if first_img is None: first_img = full_p
                            mock_count += 1
            
            # Count Product Files (Recursive)
            if product_path and os.path.exists(product_path):
                for root, dirs, files in os.walk(product_path):
                    file_count += len(files)
            
            # Update Stats Label
            stats_text = f"📊 {mock_count} Mockups | {file_count} Arq"
            self.after(0, lambda: self.stats_label.configure(text=stats_text))
            
            if first_img:
                img = Image.open(first_img)
                img.thumbnail((120, 120))
                ctk_img = ctk.CTkImage(light_image=img.copy(), dark_image=img.copy(), size=(80, 80))
                if self.winfo_exists():
                    self.after(0, lambda: self.update_photo_btn(ctk_img))
        except:
            pass

    def update_photo_btn(self, ctk_img):
        if self.winfo_exists():
            self.photo_btn.configure(image=ctk_img, text="")
            self.photo_btn.image = ctk_img
            # Force local redraw
            self.update()

    def sync_price(self, *args):
        # Update the parent dataframe in real-time
        new_price = self.price_var.get()
        self.on_save(self.index, new_price)

    def open_gallery(self):
        mockup_path = os.path.join(self.config['mockup_base_path'], str(self.data['Nome Final']))
        ImageGalleryModal(self.winfo_toplevel(), mockup_path, self.data['Nome Final'])

    def open_mockup_folder(self):
        mockup_path = os.path.join(self.config['mockup_base_path'], str(self.data['Nome Final']))
        if os.path.exists(mockup_path):
            os.startfile(mockup_path)
        else:
            messagebox.showwarning("Aviso", f"Pasta de mockup não encontrada:\n{mockup_path}")

    def open_tree(self):
        TreeModal(self.winfo_toplevel(), self.data['Nome Final'], self.data['Tree'])

    def open_folder(self):
        src_path = str(self.data['Caminho da Pasta'])
        base_src = self.config['folder_base_path_src']
        base_dst_list = self.config['folder_base_path_dst']
        
        # Ensure it's a list (backward compatibility)
        if isinstance(base_dst_list, str):
            base_dst_list = [base_dst_list]
            
        found = False
        tried_paths = []
        
        if src_path.lower().startswith(base_src.lower()):
            relative = src_path[len(base_src):].lstrip("\\/")
            
            for base_dst in base_dst_list:
                if not base_dst.strip(): continue
                dst_path = os.path.join(base_dst.strip(), relative)
                tried_paths.append(dst_path)
                
                if os.path.exists(dst_path):
                    os.startfile(dst_path)
                    found = True
                    break
        else:
            # If it doesn't start with src prefix, just try to open as is
            if os.path.exists(src_path):
                os.startfile(src_path)
                found = True
            else:
                tried_paths.append(src_path)
            
        if not found:
            paths_str = "\n".join(tried_paths)
            messagebox.showwarning("Aviso", f"Pasta não encontrada em nenhum dos destinos tentados:\n\n{paths_str}")

    def save_item(self):
        new_price = self.price_var.get()
        self.on_save(self.index, new_price)
        # Visual feedback
        self.save_btn.configure(fg_color="#1d4ed8") # Blue flash
        self.after(500, lambda: self.save_btn.configure(fg_color=COLORS["success"]))

class SettingsModal(ctk.CTkToplevel):
    def __init__(self, parent, config, on_save):
        super().__init__(parent)
        self.title("Configurações do App")
        self.geometry("600x550")
        self.attributes("-topmost", True)
        self.config = config
        self.on_save_callback = on_save
        
        self.grid_columnconfigure(0, weight=1)
        
        header = ctk.CTkLabel(self, text="⚙ Configurações de Caminhos", font=("Segoe UI", 20, "bold"))
        header.grid(row=0, column=0, padx=30, pady=30, sticky="w")
        
        # Mockup Path
        ctk.CTkLabel(self, text="Pasta Base de Mockups (FOTOS):", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, padx=30, pady=(10, 5), sticky="w")
        self.mockup_entry = ctk.CTkEntry(self, height=35)
        self.mockup_entry.grid(row=2, column=0, padx=30, pady=5, sticky="ew")
        self.mockup_entry.insert(0, config['mockup_base_path'])
        
        # Source Path
        ctk.CTkLabel(self, text="Prefixo de Origem (Remover do CSV):", font=("Segoe UI", 12, "bold")).grid(row=3, column=0, padx=30, pady=(20, 5), sticky="w")
        self.src_entry = ctk.CTkEntry(self, height=35)
        self.src_entry.grid(row=4, column=0, padx=30, pady=5, sticky="ew")
        self.src_entry.insert(0, config['folder_base_path_src'])

        # Destination Paths (Multiple)
        ctk.CTkLabel(self, text="Prefixos de Destino (Tenta um por um se não existir):", font=("Segoe UI", 12, "bold")).grid(row=5, column=0, padx=30, pady=(20, 5), sticky="w")
        self.dst_textbox = ctk.CTkTextbox(self, height=100, border_width=1, border_color="#475569")
        self.dst_textbox.grid(row=6, column=0, padx=30, pady=5, sticky="ew")
        
        dst_val = config['folder_base_path_dst']
        if isinstance(dst_val, list):
            self.dst_textbox.insert("0.0", "\n".join(dst_val))
        else:
            self.dst_textbox.insert("0.0", str(dst_val))
        
        self.save_btn = ctk.CTkButton(self, text="Salvar e Aplicar", height=45, font=("Segoe UI", 14, "bold"),
                                       fg_color=COLORS["success"], hover_color="#059669", command=self.save)
        self.save_btn.grid(row=8, column=0, padx=30, pady=20, sticky="ew")
        
        # Lock Subscription Option
        self.lock_sub_var = ctk.BooleanVar(value=config.get('lock_subscription_price', True))
        self.lock_sub_check = ctk.CTkCheckBox(self, text="Bloquear preço de Assinaturas automaticamente", variable=self.lock_sub_var,
                                               font=("Segoe UI", 12))
        self.lock_sub_check.grid(row=7, column=0, padx=30, pady=(10, 0), sticky="w")

    def save(self):
        # Get paths from textbox, splitting by newline and filtering empty lines
        dst_paths = self.dst_textbox.get("0.0", "end").strip().split("\n")
        dst_paths = [p.strip() for p in dst_paths if p.strip()]
        
        new_config = {
            **self.config,
            "mockup_base_path": self.mockup_entry.get(),
            "folder_base_path_src": self.src_entry.get(),
            "folder_base_path_dst": dst_paths,
            "lock_subscription_price": self.lock_sub_var.get()
        }
        self.on_save_callback(new_config)
        self.destroy()

class PrecificadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.config = load_config()
        ctk.set_appearance_mode(self.config.get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        
        self.title("Precificador Premium - Ciane Artes")
        self.geometry(self.config.get("window_geometry", "1300x850"))
        
        self.df = pd.DataFrame()
        self.product_rows = []
        self.current_file_path = None
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.on_search_change)
        
        # Pagination
        self.current_page = self.config.get("last_page", 0)
        self.items_per_page = 20
        self.filtered_df = pd.DataFrame()
        
        self.setup_ui()
        
        # Geometry persistence bind
        self.bind("<Configure>", self.save_window_geometry)
        
        last_csv = self.config.get("last_csv")
        if last_csv and os.path.exists(last_csv):
            self.import_csv(last_csv)
        elif os.path.exists("produtos.csv"):
            self.import_csv("produtos.csv")

    def save_window_geometry(self, event=None):
        # We use a delay to avoid saving on every single pixel movement
        if hasattr(self, "_save_geo_id"):
            self.after_cancel(self._save_geo_id)
        self._save_geo_id = self.after(1000, self._perform_geo_save)

    def _perform_geo_save(self):
        self.config["window_geometry"] = self.geometry()
        save_config(self.config)

    def setup_ui(self):
        # Top Header Area
        self.header_panel = ctk.CTkFrame(self, height=120, corner_radius=0, fg_color=(COLORS["light_card"], COLORS["dark_bg"]))
        self.header_panel.pack(side="top", fill="x")
        
        # Branding
        title_lbl = ctk.CTkLabel(self.header_panel, text="CIANE ARTES", font=("Segoe UI", 24, "bold"), text_color=COLORS["success"])
        title_lbl.place(x=25, y=20)
        subtitle_lbl = ctk.CTkLabel(self.header_panel, text="GERENCIADOR DE PREÇOS", font=("Segoe UI", 10, "bold"), text_color="#64748b")
        subtitle_lbl.place(x=25, y=55)

        # Search Bar
        self.search_entry = ctk.CTkEntry(self.header_panel, textvariable=self.search_var, placeholder_text="🔍 Pesquisar por nome ou categoria...", 
                                         width=400, height=40, corner_radius=20, border_color="#334155")
        self.search_entry.place(relx=0.5, y=40, anchor="center")

        # Controls Right
        self.ctrl_frame = ctk.CTkFrame(self.header_panel, fg_color="transparent")
        self.ctrl_frame.pack(side="right", padx=20, pady=20)
        
        self.theme_btn = ctk.CTkButton(self.ctrl_frame, text="🌓", width=40, height=40, corner_radius=20, 
                                        fg_color="#334155", hover_color="#475569", command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=5)
        
        self.settings_btn = ctk.CTkButton(self.ctrl_frame, text="⚙", width=40, height=40, corner_radius=20, 
                                           fg_color="#334155", hover_color="#475569", command=self.open_settings)
        self.settings_btn.pack(side="right", padx=5)

        # Toolbar
        self.toolbar = ctk.CTkFrame(self, height=70, corner_radius=12, fg_color=(COLORS["light_card"], COLORS["dark_card"]))
        self.toolbar.pack(side="top", fill="x", padx=20, pady=(0, 10))
        
        self.import_btn = ctk.CTkButton(self.toolbar, text="📥 Importar Lista", width=160, height=40, corner_radius=8,
                                        fg_color=COLORS["primary"], font=("Segoe UI", 13, "bold"), command=self.open_csv)
                                        
        self.import_btn.pack(side="left", padx=(15, 5), pady=15)
        
        self.refresh_btn = ctk.CTkButton(self.toolbar, text="🔄 Atualizar", width=140, height=40, corner_radius=8,
                                         fg_color="#475569", hover_color="#334155", font=("Segoe UI", 13, "bold"), command=self.refresh_list)
        self.refresh_btn.pack(side="left", padx=5, pady=15)
        
        self.export_btn = ctk.CTkButton(self.toolbar, text="📤 Exportar CSV", width=160, height=40, corner_radius=8,
                                        fg_color=COLORS["success"], font=("Segoe UI", 13, "bold"), command=self.save_csv_dialog)
        self.export_btn.pack(side="left", padx=5, pady=15)
        
        # Mass Edit Section
        ctk.CTkLabel(self.toolbar, text="|", font=("Arial", 20), text_color="#334155").pack(side="left", padx=15)
        
        self.bulk_price_entry = ctk.CTkEntry(self.toolbar, placeholder_text="Novo Preço...", width=120, height=35)
        self.bulk_price_entry.pack(side="left", padx=5, pady=15)
        
        self.bulk_btn = ctk.CTkButton(self.toolbar, text="Aplicar em Selecionados", height=35, corner_radius=6,
                                       fg_color="#7c3aed", hover_color="#6d28d9", font=("Segoe UI", 12, "bold"), command=self.mass_edit)
        self.bulk_btn.pack(side="left", padx=10, pady=15)

        # Product List Scrollable
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(side="top", fill="both", expand=True, padx=20, pady=5)
        
        # Pagination Footer
        self.footer = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.footer.pack(side="bottom", fill="x", padx=20, pady=10)
        
        self.prev_page_btn = ctk.CTkButton(self.footer, text="❮ Anterior", width=100, command=self.prev_page)
        self.prev_page_btn.pack(side="left", padx=10)
        
        self.page_info_label = ctk.CTkLabel(self.footer, text="Página 1 de 1", font=("Segoe UI", 12, "bold"))
        self.page_info_label.pack(side="left", expand=True)
        
        self.next_page_btn = ctk.CTkButton(self.footer, text="Próxima ❯", width=100, command=self.next_page)
        self.next_page_btn.pack(side="left", padx=10)
        
    def open_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path:
            self.import_csv(file_path)

    def import_csv(self, file_path):
        try:
            self.df = pd.read_csv(file_path, sep=';', quotechar='"', engine='python')
            self.df['Preço'] = self.df['Preço'].fillna('').astype(str)
            self.current_file_path = file_path
            
            # Persistence
            self.config["last_csv"] = file_path
            save_config(self.config)
            
            self.update_filtered_df()
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar arquivo:\n{e}")

    def on_search_change(self, *args):
        self.current_page = 0
        self.update_filtered_df()
        self.refresh_list()

    def update_filtered_df(self):
        query = self.search_var.get().lower()
        if not query:
            self.filtered_df = self.df.copy()
        else:
            mask = (self.df['Nome Final'].astype(str).str.lower().str.contains(query)) | \
                   (self.df['Categoria'].astype(str).str.lower().str.contains(query))
            self.filtered_df = self.df[mask].copy()

    def refresh_list(self):
        for row in self.product_rows:
            row.destroy()
        self.product_rows = []
        
        if self.filtered_df.empty:
            self.page_info_label.configure(text="Página 0 de 0")
            return

        total_pages = math.ceil(len(self.filtered_df) / self.items_per_page)
        
        # Bounds check for restored last_page
        if self.current_page >= total_pages:
            self.current_page = 0

        self.page_info_label.configure(text=f"Página {self.current_page + 1} de {total_pages} ({len(self.filtered_df)} itens)")
        
        # Save last page
        self.config["last_page"] = self.current_page
        save_config(self.config)
        
        # Check button states
        self.prev_page_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_page_btn.configure(state="normal" if self.current_page < total_pages - 1 else "disabled")

        # Slice data for current page
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_df = self.filtered_df.iloc[start_idx:end_idx]
        
        for idx, row_data in page_df.iterrows():
            p_row = ProductRow(self.scroll_frame, idx, row_data, self.config, self.on_item_save, self.on_item_select)
            p_row.pack(fill="x", pady=5, padx=5)
            self.product_rows.append(p_row)
        
        # Redraw hack - increased delay to wait for thumbnail threads
        curr_mode = ctk.get_appearance_mode()
        self.after(1000, lambda: ctk.set_appearance_mode("Light" if curr_mode == "Dark" else "Dark"))
        self.after(1500, lambda: ctk.set_appearance_mode(curr_mode))
        
        self.update_idletasks()

    def next_page(self):
        self.current_page += 1
        self.refresh_list()
        self.scroll_frame._parent_canvas.yview_moveto(0)

    def prev_page(self):
        self.current_page -= 1
        self.refresh_list()
        self.scroll_frame._parent_canvas.yview_moveto(0)

    def filter_list(self, *args):
        self.refresh_list()

    def on_item_save(self, index, new_price):
        # Update the dataframe directly using the index
        self.df.at[index, 'Preço'] = new_price
        # Auto-save to the current file
        self.auto_save_to_current_file()

    def auto_save_to_current_file(self):
        if self.current_file_path and os.path.exists(self.current_file_path):
            try:
                # Sync prices from all visible rows just to be absolutely sure
                for row in self.product_rows:
                    self.df.at[row.index, 'Preço'] = row.price_var.get()
                
                self.df.to_csv(self.current_file_path, sep=';', index=False, quoting=csv.QUOTE_ALL)
            except Exception as e:
                print(f"Erro no auto-save: {e}")

    def on_item_select(self):
        # Could update a "count" label
        pass

    def mass_edit(self):
        new_price = self.bulk_price_entry.get()
        if not new_price:
            messagebox.showwarning("Aviso", "Informe um valor para aplicar.")
            return
            
        count = 0
        for row in self.product_rows:
            if row.selected.get():
                row.price_var.set(new_price)
                self.df.at[row.index, 'Preço'] = new_price
                count += 1
        
        if count > 0:
            self.auto_save_to_current_file()
            messagebox.showinfo("Sucesso", f"Preço atualizado para {count} itens selecionados.")
        else:
            messagebox.showwarning("Aviso", "Nenhum item selecionado para alteração em massa.")

    def save_csv_dialog(self):
        if self.df.empty:
            messagebox.showwarning("Aviso", "Não há dados carregados.")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")],
                                                 initialfile="produtos_atualizados.csv")
        if file_path:
            try:
                # Sync ALL rows with the dataframe before saving
                for row in self.product_rows:
                    self.df.at[row.index, 'Preço'] = row.price_var.get()
                
                # Use standard CSV settings to match original format
                self.df.to_csv(file_path, sep=';', index=False, quoting=csv.QUOTE_ALL)
                messagebox.showinfo("Sucesso", "Arquivo exportado com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

    def toggle_theme(self):
        curr = ctk.get_appearance_mode()
        new_mode = "Light" if curr == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.config["theme"] = new_mode.lower()
        save_config(self.config)

    def open_settings(self):
        SettingsModal(self, self.config, self.update_config)

    def update_config(self, new_config):
        self.config = new_config
        save_config(self.config)
        self.refresh_list()

if __name__ == "__main__":
    # Windows High DPI support
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = PrecificadorApp()
    app.mainloop()

