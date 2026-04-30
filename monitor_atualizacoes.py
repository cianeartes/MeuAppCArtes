#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║          Monitor de Atualizações  v2.0                      ║
║  Monitoramento de pastas com histórico, favoritos e listas  ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import datetime
import threading
import subprocess
import sys
import csv
import uuid
import multiprocessing
import customtkinter
import ctypes

# Configurações do CustomTkinter
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def resource_path(relative_path):
    """ Obtém o caminho absoluto para recursos, funciona para dev e PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ICONS_DIR = "icones_app"

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES GLOBAIS
# ══════════════════════════════════════════════════════════════════════════════
APP_NAME    = "Monitor de Atualizações"
APP_VERSION = "2.0"
DATA_FILE   = "monitor_dados.json"
MAX_ITENS   = 100_000

# ══════════════════════════════════════════════════════════════════════════════
# PALETA DE TEMAS
# ══════════════════════════════════════════════════════════════════════════════
TEMAS = {
    "dark": {
        "bg":            "#050505",
        "panel":         "#0d0d0d",
        "card":          "#141414",
        "fg":            "#ffffff",
        "subfg":         "#a0a0a0",
        "entry_bg":      "#1a1a1a",
        "entry_fg":      "#ffffff",
        "btn":           "#9061ff",
        "btn_fg":        "#ffffff",
        "btn_hover":     "#a885ff",
        "accent":        "#00d4ff",
        "green":         "#00ff88",
        "green_bg":      "#002211",
        "red":           "#ff4444",
        "red_bg":        "#220000",
        "tree_bg":       "#050505",
        "tree_fg":       "#f0f0f0",
        "tree_sel":      "#1a1a1a",
        "heading_bg":    "#0d0d0d",
        "heading_fg":    "#9061ff",
        "border":        "#222222",
        "topbar_bg":     "#000000",
        "sidebar_bg":    "#0d0d0d",
        "sidebar_ativo": "#1a1a1a",
        "sidebar_hover": "#141414",
        "status_bg":     "#000000",
        "scrollbar":     "#333333",
        "sep":           "#1a1a1a",
        "progress":      "#9061ff",
    },
    "light": {
        "bg":            "#fcfcfc",
        "panel":         "#ffffff",
        "card":          "#f8f8f8",
        "fg":            "#1a1a1a",
        "subfg":         "#666666",
        "entry_bg":      "#ffffff",
        "entry_fg":      "#1a1a1a",
        "btn":           "#5c2dff",
        "btn_fg":        "#ffffff",
        "btn_hover":     "#7c4dff",
        "accent":        "#007bff",
        "green":         "#008a45",
        "green_bg":      "#e6f4ea",
        "red":           "#d93025",
        "red_bg":        "#fce8e6",
        "tree_bg":       "#ffffff",
        "tree_fg":       "#1a1a1a",
        "tree_sel":      "#f0f0f0",
        "heading_bg":    "#ffffff",
        "heading_fg":    "#5c2dff",
        "border":        "#e0e0e0",
        "topbar_bg":     "#ffffff",
        "sidebar_bg":    "#f8f8f8",
        "sidebar_ativo": "#ffffff",
        "sidebar_hover": "#f0f0f0",
        "status_bg":     "#ffffff",
        "scrollbar":     "#d0d0d0",
        "sep":           "#eeeeee",
        "progress":      "#5c2dff",
    }
}

MAPA_ICONES_PADRAO = {
    "pasta":   "📁",
    "arquivo": "📄",
    "pdf":     "📕",
    "zip":     "📦",
    "rar":     "📦",
    "exe":     "⚙️",
    "txt":     "📝",
    "jpg":     "🖼️",
    "png":     "🖼️",
    "mp4":     "🎬",
    "xlsx":    "📊",
    "docx":    "📝",
    "csv":     "📈"
}

# ══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════════════════
def fmt_data(ts):
    try:
        return datetime.datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return ''

def fmt_tamanho(n):
    for u in ['B','KB','MB','GB','TB']:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"

def abrir_no_explorador(caminho):
    """Abre pasta/arquivo no gerenciador de arquivos do sistema operacional."""
    if not os.path.exists(caminho):
        messagebox.showerror("Erro", f"Caminho não encontrado:\n{caminho}")
        return
    try:
        if sys.platform == 'win32':
            if os.path.isfile(caminho):
                subprocess.run(['explorer', '/select,', caminho])
            else:
                os.startfile(caminho)
        elif sys.platform == 'darwin':
            subprocess.run(['open', caminho])
        else:
            subprocess.run(['xdg-open', caminho])
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir:\n{caminho}\n\n{e}")

# ══════════════════════════════════════════════════════════════════════════════
# CALENDÁRIO POPUP (CUSTOM)
# ══════════════════════════════════════════════════════════════════════════════
class CalendarioPopUp(customtkinter.CTkToplevel):
    def __init__(self, master, var, tema):
        super().__init__(master)
        self.title("Selecionar Data")
        self.geometry("300x380")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.var = var
        self.tema = tema

        # Centralizar
        self.update_idletasks()
        w, h = 300, 380
        x = master.winfo_x() + (master.winfo_width() // 2) - (w // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        now = datetime.datetime.now()
        self.mes = now.month
        self.ano = now.year
        self.hoje = now.day

        self.frame_corpo = customtkinter.CTkFrame(self)
        self.frame_corpo.pack(fill='both', expand=True, padx=10, pady=10)

        self.desenhar()

    def desenhar(self):
        for w in self.frame_corpo.winfo_children():
            w.destroy()

        header = customtkinter.CTkFrame(self.frame_corpo, fg_color="transparent")
        header.pack(fill='x', pady=10)

        customtkinter.CTkButton(header, text="<", width=35, command=self.mes_ant).pack(side='left', padx=10)
        
        meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        customtkinter.CTkLabel(header, text=f"{meses[self.mes]} {self.ano}", 
                              font=("Segoe UI", 12, "bold")).pack(side='left', expand=True)

        customtkinter.CTkButton(header, text=">", width=35, command=self.mes_prox).pack(side='right', padx=10)

        dias_f = customtkinter.CTkFrame(self.frame_corpo, fg_color="transparent")
        dias_f.pack(fill='both', expand=True, padx=5)

        for i, d in enumerate(["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]):
            customtkinter.CTkLabel(dias_f, text=d, font=("Segoe UI", 10), text_color="gray").grid(row=0, column=i, pady=5)

        import calendar
        cal = calendar.monthcalendar(self.ano, self.mes)

        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day == 0: continue
                
                is_hoje = (day == self.hoje and self.mes == datetime.datetime.now().month and self.ano == datetime.datetime.now().year)
                
                btn = customtkinter.CTkButton(
                    dias_f, text=str(day), width=35, height=35,
                    fg_color=self.tema['btn'] if is_hoje else "transparent",
                    text_color=self.tema['btn_fg'] if is_hoje else self.tema['fg'],
                    hover_color=self.tema['btn_hover'],
                    command=lambda d=day: self.selecionar(d)
                )
                btn.grid(row=r+1, column=c, padx=2, pady=2)

    def mes_ant(self):
        self.mes -= 1
        if self.mes < 1: self.mes = 12; self.ano -= 1
        self.desenhar()

    def mes_prox(self):
        self.mes += 1
        if self.mes > 12: self.mes = 1; self.ano += 1
        self.desenhar()

    def selecionar(self, dia):
        data_str = f"{dia:02d}/{self.mes:02d}/{self.ano}"
        self.var.set(data_str)
        self.destroy()

def detectar_novidades(itens_novos, itens_antigos):
    """Compara duas listas de itens e retorna adições e modificações."""
    mapa_antigo = {it['caminho']: it['modificacao'] for it in itens_antigos}
    novos, modificados = [], []
    for it in itens_novos:
        cam = it['caminho']
        if cam not in mapa_antigo:
            novos.append(it)
        elif it['modificacao'] > mapa_antigo[cam]:
            modificados.append(it)
    removidos = [cam for cam in mapa_antigo if cam not in {it['caminho'] for it in itens_novos}]
    return novos, modificados, removidos


# ══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1100x700")

        # Solução definitiva para ícone no Windows (Barra de Tarefas e Janela)
        icon_path = resource_path("busca.ico")
        if os.path.exists(icon_path):
            try:
                # 1. Registrar ID do App no Windows
                myappid = f"cianeartes.monitor.atualizacoes.{APP_VERSION}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                
                # 2. Aplicar ícone com pequeno delay para garantir sobreposição ao padrão do CTk
                self.root.after(200, lambda: self.root.iconbitmap(icon_path))
            except Exception:
                pass
        
        self.root.minsize(950, 620)

        # ── Estado ──────────────────────────────────────────────────────────
        self.tema_nome  = "dark"
        self.tema       = TEMAS["dark"]
        self.listas     = {}          # { lid: {...} }
        self.icones     = MAPA_ICONES_PADRAO.copy()
        self.icones_img = {}          # Cache de PhotoImages {ext: img}
        self.lista_ativa = None       # lid ativo
        self.escaneando  = False
        self._parar_scan = threading.Event()  # Sinal de cancelamento
        self.aba_ativa   = "todos"    # "todos" | "favoritos"

        self.var_arquivos = tk.BooleanVar(value=False)

        # ── Inicialização ────────────────────────────────────────────────────
        self.carregar_dados()
        self.carregar_icones_externos()
        
        # Aplicar modo de aparência do CTk
        customtkinter.set_appearance_mode("Dark" if self.tema_nome == "dark" else "Light")
        
        self._criar_ui()
        self.aplicar_tema()
        self.atualizar_sidebar()

        # Selecionar primeira lista ao abrir
        if self.listas:
            self.selecionar_lista(list(self.listas.keys())[0])

        self.root.protocol("WM_DELETE_WINDOW", self._on_fechar)

    # ══════════════════════════════════════════════════════════════════════
    # PERSISTÊNCIA
    # ══════════════════════════════════════════════════════════════════════
    def carregar_dados(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                self.listas    = d.get('listas', {})
                self.tema_nome = d.get('tema', 'dark')
                self.icones    = d.get('icones', MAPA_ICONES_PADRAO.copy())
                self.tema      = TEMAS.get(self.tema_nome, TEMAS['dark'])
            except Exception:
                self.listas = {}
                self.icones = MAPA_ICONES_PADRAO.copy()
        else:
            self.listas = {}
            self.icones = MAPA_ICONES_PADRAO.copy()

    def salvar_dados(self):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'listas': self.listas, 
                    'tema':   self.tema_nome, 
                    'icones': self.icones
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar: {e}")

    def carregar_icones_externos(self):
        """Carrega imagens da pasta icones_app para o Treeview."""
        if not os.path.exists(ICONS_DIR):
            os.makedirs(ICONS_DIR)
        
        if not HAS_PIL: return

        for f in os.listdir(ICONS_DIR):
            name, ext = os.path.splitext(f)
            if ext.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                try:
                    path = os.path.join(ICONS_DIR, f)
                    img = Image.open(path)
                    img = img.resize((20, 20), Image.Resampling.LANCZOS)
                    self.icones_img[name.lower()] = ImageTk.PhotoImage(img)
                except Exception as e:
                    print(f"Erro ao carregar ícone {f}: {e}")

    def _on_fechar(self):
        self.salvar_dados()
        self.root.destroy()

    # ══════════════════════════════════════════════════════════════════════
    # GERENCIAMENTO DE TEMA
    # ══════════════════════════════════════════════════════════════════════
    def alternar_tema(self):
        if self.tema_nome == "dark":
            self.tema_nome = "light"
            customtkinter.set_appearance_mode("Light")
        else:
            self.tema_nome = "dark"
            customtkinter.set_appearance_mode("Dark")
        
        self.tema = TEMAS[self.tema_nome]
        self.aplicar_tema()
        self.salvar_dados()

    def aplicar_tema(self):
        t = self.tema
        # Cores de fundo dos containers principais
        self.frame_root.configure(fg_color=t['bg'])
        self.topbar.configure(fg_color=t['topbar_bg'])
        
        if hasattr(self, 'frame_corpo'):
            self.frame_corpo.configure(fg_color=t['bg'])
            
        if hasattr(self, 'sidebar'):
            self.sidebar.configure(fg_color=t['sidebar_bg'])
            
        if hasattr(self, 'frame_itens_sb'):
            self.frame_itens_sb.configure(fg_color=t['sidebar_bg'])
            
        self.frame_main.configure(fg_color=t['bg'])
        self.frame_status.configure(fg_color=t['status_bg'])
        
        # Labels da topbar
        self.lbl_titulo.configure(text_color=t['fg'])
        self.btn_tema.configure(
            text="☀️" if self.tema_nome == "dark" else "🌙",
            fg_color=t['card'],
            text_color=t['fg'],
            hover_color=t['btn_hover']
        )
        self.btn_ajuda.configure(
            fg_color=t['card'],
            text_color=t['fg'],
            hover_color=t['btn_hover']
        )
        self.btn_config.configure(
            fg_color=t['card'],
            text_color=t['fg'],
            hover_color=t['btn_hover']
        )
        
        # Estilos da Treeview (Tkinter legado precisa de Style())
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                        background=t['tree_bg'], 
                        foreground=t['tree_fg'], 
                        fieldbackground=t['tree_bg'],
                        borderwidth=0,
                        font=("Segoe UI", 11),
                        rowheight=35)
        style.map("Treeview", background=[('selected', t['tree_sel'])], foreground=[('selected', t['tree_fg'])])
        
        style.configure("Treeview.Heading", 
                        background=t['heading_bg'], 
                        foreground=t['heading_fg'], 
                        relief="flat",
                        font=("Segoe UI", 10, "bold"))
        
        # Tags de linha
        self.tree.tag_configure('favorito', foreground=t['green'])
        
        self._estilo_abas(t)
        self.atualizar_sidebar()

    def _estilo_abas(self, t):
        if self.aba_ativa == "todos":
            self.btn_aba_todos.configure(fg_color=t['btn'], text_color=t['btn_fg'])
            self.btn_aba_favs.configure(fg_color="transparent", text_color=t['subfg'])
        else:
            self.btn_aba_todos.configure(fg_color="transparent", text_color=t['subfg'])
            self.btn_aba_favs.configure(fg_color=t['btn'], text_color=t['btn_fg'])

    # ══════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO DA UI
    # ══════════════════════════════════════════════════════════════════════
    def _criar_ui(self):
        # Frame raiz
        self.frame_root = customtkinter.CTkFrame(self.root, corner_radius=0)
        self.frame_root.pack(fill='both', expand=True)

        self._criar_topbar()

        # Corpo: sidebar + área principal
        self.frame_corpo = customtkinter.CTkFrame(self.frame_root, corner_radius=0)
        self.frame_corpo.pack(fill='both', expand=True)

        self._criar_sidebar()
        
        # Área principal (Main Content)
        self.frame_main = customtkinter.CTkFrame(self.frame_corpo, corner_radius=0)
        self.frame_main.pack(side='left', fill='both', expand=True)

        self._criar_area_principal()
        self._criar_statusbar()

    # ── Topbar ───────────────────────────────────────────────────────────────
    def _criar_topbar(self):
        self.topbar = customtkinter.CTkFrame(self.frame_root, height=70, corner_radius=0)
        self.topbar.pack(fill='x')
        self.topbar.pack_propagate(False)

        self.lbl_titulo = customtkinter.CTkLabel(
            self.topbar,
            text="📡  Monitor de Atualizações",
            font=("Segoe UI", 18, "bold")
        )
        self.lbl_titulo.pack(side='left', padx=25, pady=15)

        # Botão tema circular premium
        self.btn_tema = customtkinter.CTkButton(
            self.topbar, text="🌙",
            font=("Segoe UI", 14), width=45, height=45,
            corner_radius=22,
            command=self.alternar_tema
        )
        self.btn_tema.pack(side='right', padx=15, pady=10)

        self.btn_ajuda = customtkinter.CTkButton(
            self.topbar, text="?",
            font=("Segoe UI", 14, "bold"), width=45, height=45,
            corner_radius=22,
            command=self._mostrar_ajuda
        )
        self.btn_ajuda.pack(side='right', padx=5, pady=10)

        self.btn_config = customtkinter.CTkButton(
            self.topbar, text="⚙️",
            font=("Segoe UI", 14), width=45, height=45,
            corner_radius=22,
            command=self.abrir_configuracoes
        )
        self.btn_config.pack(side='right', padx=5, pady=10)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    def _criar_sidebar(self):
        # Sidebar Container
        self.sidebar = customtkinter.CTkFrame(self.frame_corpo, width=280, corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Cabeçalho
        self.frame_sb_header = customtkinter.CTkFrame(self.sidebar, fg_color="transparent")
        self.frame_sb_header.pack(fill='x', padx=15, pady=(20, 10))

        self.lbl_sb_titulo = customtkinter.CTkLabel(
            self.frame_sb_header,
            text="MINHAS LISTAS",
            font=("Segoe UI", 10, "bold")
        )
        self.lbl_sb_titulo.pack(side='left')

        self.btn_nova = customtkinter.CTkButton(
            self.frame_sb_header, text="＋",
            font=("Segoe UI", 16, "bold"),
            width=32, height=32,
            command=self.nova_lista
        )
        self.btn_nova.pack(side='right')

        # Scrollable Frame nativo do CustomTkinter
        self.frame_itens_sb = customtkinter.CTkScrollableFrame(
            self.sidebar, corner_radius=0, fg_color="transparent"
        )
        self.frame_itens_sb.pack(fill='both', expand=True, padx=5)

        self.lbl_versao = customtkinter.CTkLabel(
            self.sidebar,
            text=f"v{APP_VERSION}",
            font=("Segoe UI", 9),
            text_color="gray"
        )
        self.lbl_versao.pack(fill='x', pady=10)

    def _criar_statusbar(self):
        self.frame_status = customtkinter.CTkFrame(self.root, height=35, corner_radius=0)
        self.frame_status.pack(fill='x', side='bottom')

        self.lbl_status = customtkinter.CTkLabel(self.frame_status, text="Pronto.", font=("Segoe UI", 11))
        self.lbl_status.pack(side='left', padx=20)

        self.lbl_contagem = customtkinter.CTkLabel(self.frame_status, text="", font=("Segoe UI", 11))
        self.lbl_contagem.pack(side='right', padx=20)

        self.lbl_ultimo_scan = customtkinter.CTkLabel(self.frame_status, text="", font=("Segoe UI", 11))
        self.lbl_ultimo_scan.pack(side='right', padx=20)

    # ── Área principal ───────────────────────────────────────────────────────
    def _criar_area_principal(self):
        self.frame_toolbar = customtkinter.CTkFrame(self.frame_main, fg_color="transparent")
        self.frame_toolbar.pack(fill='x', padx=20, pady=20)

        # PRIMEIRA LINHA
        linha = customtkinter.CTkFrame(self.frame_toolbar, fg_color="transparent")
        linha.pack(fill='x')

        customtkinter.CTkLabel(linha, text="Pasta Base:", font=("Segoe UI", 13, "bold")).pack(side='left', padx=(0, 10))
        self.entry_pasta = customtkinter.CTkEntry(linha, placeholder_text="Selecione a pasta para monitorar...", font=("Segoe UI", 13), height=36)
        self.entry_pasta.pack(side='left', padx=(0, 10), fill='x', expand=True)

        customtkinter.CTkButton(linha, text="Explorar...", width=110, height=36, font=("Segoe UI", 13),
                               command=self.escolher_pasta).pack(side='left', padx=(0, 15))

        customtkinter.CTkLabel(linha, text="Nível:", font=("Segoe UI", 13, "bold")).pack(side='left', padx=(0, 5))
        self.spin_nivel = customtkinter.CTkEntry(linha, width=55, font=("Segoe UI", 13), height=36)
        self.spin_nivel.insert(0, "2")
        self.spin_nivel.pack(side='left', padx=(0, 15))

        self.chk_arq = customtkinter.CTkCheckBox(linha, text="Arquivos", variable=self.var_arquivos, font=("Segoe UI", 13))
        self.chk_arq.pack(side='left', padx=(0, 15))

        self.btn_scan = customtkinter.CTkButton(linha, text="Escanear", font=("Segoe UI", 13, "bold"),
                                              width=130, height=36, command=self.iniciar_scan_thread)
        self.btn_scan.pack(side='left', padx=(0, 10))

        self.btn_parar = customtkinter.CTkButton(
            linha, text="⏹ Parar", font=("Segoe UI", 13, "bold"),
            width=110, height=36,
            fg_color="#c0392b", hover_color="#e74c3c", text_color="#ffffff",
            command=self._cancelar_scan
        )
        # Não faz pack aqui — aparece só durante o scan

        # SEGUNDA LINHA
        linha2 = customtkinter.CTkFrame(self.frame_toolbar, fg_color="transparent")
        linha2.pack(fill='x', pady=(15, 0))

        customtkinter.CTkLabel(linha2, text="📅 De:", font=("Segoe UI", 13, "bold")).pack(side='left', padx=(0, 5))
        self.var_data_inicio = tk.StringVar(value="01/01/2026")
        self.entry_inicio = customtkinter.CTkEntry(linha2, textvariable=self.var_data_inicio, width=110, font=("Segoe UI", 13), height=36)
        self.entry_inicio.pack(side='left', padx=(0, 5))

        customtkinter.CTkButton(linha2, text="📅", width=36, height=36, font=("Segoe UI", 13),
                               command=lambda: CalendarioPopUp(self.root, self.var_data_inicio, self.tema)).pack(side='left', padx=(0, 10))

        customtkinter.CTkLabel(linha2, text="Até:", font=("Segoe UI", 13, "bold")).pack(side='left', padx=(0, 5))
        self.var_data_fim = tk.StringVar(value=datetime.datetime.now().strftime("%d/%m/%Y"))
        self.entry_fim = customtkinter.CTkEntry(linha2, textvariable=self.var_data_fim, width=110, font=("Segoe UI", 13), height=36)
        self.entry_fim.pack(side='left', padx=(0, 5))

        customtkinter.CTkButton(linha2, text="📅", width=36, height=36, font=("Segoe UI", 13),
                               command=lambda: CalendarioPopUp(self.root, self.var_data_fim, self.tema)).pack(side='left', padx=(0, 15))

        self.btn_filtrar_data = customtkinter.CTkButton(linha2, text="Filtrar", width=90, height=36, font=("Segoe UI", 13),
                                                      command=self.recarregar_aba_atual)
        self.btn_filtrar_data.pack(side='left', padx=(0, 20))

        customtkinter.CTkLabel(linha2, text="🔍 Busca:", font=("Segoe UI", 13, "bold")).pack(side='left', padx=(0, 5))
        self.var_busca = tk.StringVar()
        self.entry_busca = customtkinter.CTkEntry(linha2, textvariable=self.var_busca,
                                                 placeholder_text="🔍 Pesquisar nos resultados...",
                                                 font=("Segoe UI", 13), height=36)
        self.entry_busca.pack(side='left', fill='x', expand=True)
        self.var_busca.trace_add("write", lambda *args: self.recarregar_aba_atual())

        # Progress
        self.frame_progress = customtkinter.CTkFrame(self.frame_toolbar, fg_color="transparent")
        self.frame_progress.pack(fill='x', pady=(10, 0))
        self.lbl_progress = customtkinter.CTkLabel(self.frame_progress, text="", font=("Segoe UI", 12))
        self.lbl_progress.pack(side='left')
        self.progress_bar = customtkinter.CTkProgressBar(self.frame_progress, width=300)

        self._criar_abas()
        self._criar_treeview()

    def _criar_abas(self):
        self.frame_abas_outer = customtkinter.CTkFrame(self.frame_main, fg_color="transparent")
        self.frame_abas_outer.pack(fill='x', padx=20, pady=(0, 10))

        self.frame_abas = customtkinter.CTkFrame(self.frame_abas_outer, fg_color="#222222") # Pill background
        self.frame_abas.pack(side='left')

        self.btn_aba_todos = customtkinter.CTkButton(
            self.frame_abas, text="📋 Todos",
            width=100, corner_radius=15,
            command=lambda: self.trocar_aba("todos")
        )
        self.btn_aba_todos.pack(side='left', padx=2, pady=2)

        self.btn_aba_favs = customtkinter.CTkButton(
            self.frame_abas, text="⭐ Favoritos",
            width=100, corner_radius=15,
            command=lambda: self.trocar_aba("favoritos")
        )
        self.btn_aba_favs.pack(side='left', padx=2, pady=2)

        self.lbl_lista_nome = customtkinter.CTkLabel(
            self.frame_abas_outer, text="Lista: Nenhuma",
            font=("Segoe UI", 11, "bold")
        )
        self.lbl_lista_nome.pack(side='right')

    def _criar_treeview(self):
        self.frame_tree = customtkinter.CTkFrame(self.frame_main, fg_color="transparent")
        self.frame_tree.pack(fill='both', expand=True, padx=20, pady=(0, 10))

        cols = ('fav', 'tipo', 'nome', 'caminho', 'criacao', 'modificacao')
        self.tree = ttk.Treeview(
            self.frame_tree, columns=cols, show='tree headings', selectmode='browse'
        )

        # Configurar coluna de Ícone (Tree column #0)
        self.tree.column('#0', width=40, minwidth=40, stretch=False, anchor='center')
        self.tree.heading('#0', text='', anchor='center')

        # Cabeçalhos
        self.tree.heading('fav',         text='★',            anchor='center')
        self.tree.heading('tipo',        text='Tipo',         anchor='center')
        self.tree.heading('nome',        text='Nome',         anchor='w')
        self.tree.heading('caminho',     text='Caminho',      anchor='w')
        self.tree.heading('criacao',     text='Criação',      anchor='center')
        self.tree.heading('modificacao', text='Modificação',  anchor='center')

        # Larguras
        self.tree.column('fav',         width=45,  minwidth=45,  stretch=False, anchor='center')
        self.tree.column('tipo',        width=105, minwidth=80,  stretch=False, anchor='center')
        self.tree.column('nome',        width=270, minwidth=140, anchor='w')
        self.tree.column('caminho',     width=400, minwidth=180, anchor='w')
        self.tree.column('criacao',     width=148, minwidth=130, stretch=False, anchor='center')
        self.tree.column('modificacao', width=148, minwidth=130, stretch=False, anchor='center')

        # Scrollbars modernas (CustomTkinter)
        sb_y = customtkinter.CTkScrollbar(self.frame_tree, orientation='vertical', command=self.tree.yview)
        sb_x = customtkinter.CTkScrollbar(self.frame_tree, orientation='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        sb_y.grid(row=0, column=1, sticky='ns', padx=(2, 0))
        sb_x.grid(row=1, column=0, sticky='ew', pady=(2, 0))
        self.frame_tree.grid_rowconfigure(0, weight=1)
        self.frame_tree.grid_columnconfigure(0, weight=1)

        # Eventos
        self.tree.bind('<Double-1>',        self._duplo_clique)
        self.tree.bind('<ButtonRelease-1>', self._clique_simples)
        self.tree.bind('<Button-3>',        self._menu_contexto)

        # Menu de contexto
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="📂 Abrir pasta",        command=self._ctx_abrir)
        self.ctx_menu.add_command(label="⭐ Favoritar / Desfav.", command=self._ctx_favoritar)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="📋 Copiar caminho",      command=self._ctx_copiar_caminho)
        self.ctx_menu.add_command(label="📋 Copiar nome",         command=self._ctx_copiar_nome)

        self._row_ctx = None  # linha do context menu

    # ── Sidebar – Gerenciamento de Listas ─────────────────────────────────────

    # ══════════════════════════════════════════════════════════════════════
    # SIDEBAR – GERENCIAMENTO DE LISTAS
    # ══════════════════════════════════════════════════════════════════════
    def atualizar_sidebar(self):
        for w in self.frame_itens_sb.winfo_children():
            w.destroy()

        if not self.listas:
            customtkinter.CTkLabel(
                self.frame_itens_sb,
                text="Nenhuma lista.\nClique em ＋ para criar.",
                font=("Segoe UI", 11),
                text_color="gray"
            ).pack(pady=30)
        else:
            for lid, lista in self.listas.items():
                self._item_sidebar(lid, lista)

    def _item_sidebar(self, lid, lista):
        ativo = (lid == self.lista_ativa)
        t = self.tema
        
        # Frame de item da sidebar
        btn_container = customtkinter.CTkFrame(self.frame_itens_sb, fg_color="transparent")
        btn_container.pack(fill='x', pady=2)

        # Botão principal do item
        n_itens = len(lista.get('itens', []))
        texto = f"📂  {lista.get('nome', 'Lista')}\n    {n_itens} itens"
        
        btn = customtkinter.CTkButton(
            btn_container,
            text=texto,
            anchor='w',
            font=("Segoe UI", 11, "bold" if ativo else "normal"),
            fg_color=t['btn'] if ativo else "transparent",
            text_color=t['btn_fg'] if ativo else t['fg'],
            hover_color=t['btn_hover'] if ativo else t['card'],
            height=50,
            command=lambda l=lid: self.selecionar_lista(l)
        )
        btn.pack(side='left', fill='x', expand=True, padx=(0, 5))

        # Botão de deletar pequeno e elegante
        btn_del = customtkinter.CTkButton(
            btn_container, text="✕",
            width=30, height=50,
            fg_color="transparent",
            text_color="gray",
            hover_color=t['red'],
            command=lambda l=lid: self.deletar_lista(l)
        )
        btn_del.pack(side='right')

    # ── Ações de lista ───────────────────────────────────────────────────────
    def nova_lista(self):
        nome = simpledialog.askstring(
            "Nova Lista", "Nome da nova lista:",
            parent=self.root
        )
        if not nome or not nome.strip():
            return
        lid = str(uuid.uuid4())[:8]
        self.listas[lid] = {
            'nome':        nome.strip(),
            'pasta_base':  '',
            'profundidade': 5,
            'ultimo_scan': '',
            'itens':       [],
            'favoritos':   []
        }
        self.salvar_dados()
        self.atualizar_sidebar()
        self.selecionar_lista(lid)

    def deletar_lista(self, lid):
        nome = self.listas[lid].get('nome', '')
        if not messagebox.askyesno(
            "Confirmar exclusão",
            f"Excluir a lista '{nome}'?\nEsta ação não pode ser desfeita.",
            parent=self.root
        ):
            return
        del self.listas[lid]
        if self.lista_ativa == lid:
            self.lista_ativa = None
            self.tree.delete(*self.tree.get_children())
            self.lbl_lista_nome.configure(text="Selecione ou crie uma lista →")
            self.entry_pasta.delete(0, tk.END)
            self.lbl_contagem.configure(text="")
            self.lbl_ultimo_scan.configure(text="")
        self.salvar_dados()
        self.atualizar_sidebar()

    def renomear_lista(self):
        if not self.lista_ativa:
            messagebox.showwarning("Aviso", "Selecione uma lista para renomear.", parent=self.root)
            return
        nome_atual = self.listas[self.lista_ativa].get('nome', '')
        novo_nome = simpledialog.askstring(
            "Renomear Lista", "Novo nome:",
            initialvalue=nome_atual, parent=self.root
        )
        if novo_nome and novo_nome.strip():
            self.listas[self.lista_ativa]['nome'] = novo_nome.strip()
            self.lbl_lista_nome.configure(text=f"Lista: {novo_nome.strip()}")
            self.salvar_dados()
            self.atualizar_sidebar()

    def selecionar_lista(self, lid):
        if lid not in self.listas:
            return
        self.lista_ativa = lid
        lista = self.listas[lid]

        # Carregar valores na toolbar
        self.entry_pasta.delete(0, tk.END)
        self.entry_pasta.insert(0, lista.get('pasta_base', ''))
        self.spin_nivel.delete(0, 'end')
        self.spin_nivel.insert(0, str(lista.get('profundidade', 5)))
        self.lbl_lista_nome.configure(text=f"Lista: {lista['nome']}")

        scan_dt = lista.get('ultimo_scan', '')
        self.lbl_ultimo_scan.configure(
            text=f"Último scan: {scan_dt}" if scan_dt else ""
        )

        # Recarregar tree
        self.carregar_tree(lista)
        self.atualizar_sidebar()

    # ══════════════════════════════════════════════════════════════════════
    # ABAS
    # ══════════════════════════════════════════════════════════════════════
    def trocar_aba(self, aba):
        self.aba_ativa = aba
        self._estilo_abas(self.tema)
        self.recarregar_aba_atual()

    def recarregar_aba_atual(self):
        if self.lista_ativa:
            self.carregar_tree(self.listas[self.lista_ativa])

    # ══════════════════════════════════════════════════════════════════════
    # CARREGAR TREE
    # ══════════════════════════════════════════════════════════════════════
    def carregar_tree(self, lista):
        self.tree.delete(*self.tree.get_children())
        itens    = lista.get('itens', [])
        favoritos = set(lista.get('favoritos', []))

        # 1. Filtro de Aba
        if self.aba_ativa == "favoritos":
            itens = [it for it in itens if it['caminho'] in favoritos]

        # 2. Filtro de Data (Período Customizado)
        try:
            inicio_str = self.var_data_inicio.get().strip()
            fim_str    = self.var_data_fim.get().strip()
            
            ts_inicio = 0
            ts_fim    = float('inf')

            if inicio_str:
                ts_inicio = datetime.datetime.strptime(inicio_str, "%d/%m/%Y").timestamp()
            if fim_str:
                # Fim do dia escolhido (23:59:59)
                ts_fim = datetime.datetime.strptime(fim_str, "%d/%m/%Y").replace(hour=23, minute=59, second=59).timestamp()

            itens = [it for it in itens if ts_inicio <= it.get('mod_ts', 0) <= ts_fim]
        except ValueError:
            # Se a data for inválida, apenas não filtra (ou mostra erro silencioso)
            pass

        # 3. Filtro de Busca
        busca = self.var_busca.get().lower().strip()
        if busca:
            itens = [it for it in itens if busca in it['nome'].lower() or busca in it['caminho'].lower()]

        for item in itens:
            cam   = item['caminho']
            is_fav = cam in favoritos
            icone_fav  = "⭐" if is_fav else "☆"
            tags   = ('favorito',) if is_fav else ()

            # Buscar imagem real do cache
            tipo_id = item.get('tipo_id', 'arquivo').lower()
            img = self.icones_img.get(tipo_id)
            if not img: # Tentar padrão se não achar específico
                img = self.icones_img.get('arquivo' if item.get('tipo_id') != 'pasta' else 'pasta')

            self.tree.insert('', tk.END, values=(
                icone_fav,
                item.get('tipo', ''),
                item.get('nome', ''),
                cam,
                item.get('criacao', ''),
                item.get('modificacao', '')
            ), tags=tags, image=img if img else "")

        n_total = len(lista.get('itens', []))
        n_view  = len(itens)
        n_favs  = len(favoritos)
        extra   = f" (filtrando {n_view})" if self.aba_ativa == "favoritos" else ""
        self.lbl_contagem.configure(
            text=f"{n_total} item(ns){extra}  •  ⭐ {n_favs}"
        )

    # ══════════════════════════════════════════════════════════════════════
    # SCAN / ESCANEAMENTO
    # ══════════════════════════════════════════════════════════════════════
    def escolher_pasta(self):
        pasta = filedialog.askdirectory(parent=self.root, title="Selecionar pasta base")
        if pasta:
            self.entry_pasta.delete(0, tk.END)
            self.entry_pasta.insert(0, pasta)

    def _cancelar_scan(self):
        """Sinaliza para o scan em andamento que deve parar."""
        self._parar_scan.set()
        self.btn_parar.configure(state='disabled', text="Parando...")
        self.lbl_status.configure(text="⏹ Cancelando scan...")

    def iniciar_scan_thread(self):
        if self.escaneando:
            return
        if not self.lista_ativa:
            messagebox.showwarning("Aviso", "Selecione ou crie uma lista primeiro.", parent=self.root)
            return
        self._parar_scan.clear()  # Garante que a flag está limpa
        t = threading.Thread(target=self._executar_scan, daemon=True)
        t.start()

    def _executar_scan(self):
        self.escaneando = True
        self.root.after(0, self._inicio_ui_scan)

        pasta = self.entry_pasta.get().strip()
        if not pasta or not os.path.isdir(pasta):
            self.root.after(0, lambda: messagebox.showerror("Erro", "Pasta inválida ou não encontrada.", parent=self.root))
            self.root.after(0, self._fim_ui_scan)
            return

        try:
            nivel = max(1, min(20, int(self.spin_nivel.get())))
        except ValueError:
            nivel = 5

        incluir_arq = self.var_arquivos.get()
        itens_novos = self._escanear(pasta, nivel, incluir_arq)

        # Verificar se foi cancelado
        if self._parar_scan.is_set():
            self.root.after(0, lambda n=len(itens_novos): self._scan_cancelado(n))
            return

        # Detectar novidades vs scan anterior
        lista = self.listas[self.lista_ativa]
        itens_antigos = lista.get('itens', [])
        novos, modificados, removidos = detectar_novidades(itens_novos, itens_antigos)

        # Atualizar dados
        lista['pasta_base']   = pasta
        lista['profundidade'] = nivel
        lista['ultimo_scan']  = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        # Manter só favoritos que ainda existem
        caminhos_novos = {it['caminho'] for it in itens_novos}
        lista['favoritos'] = [f for f in lista.get('favoritos', []) if f in caminhos_novos]
        lista['itens'] = itens_novos

        self.salvar_dados()

        self.root.after(0, lambda: self._pos_scan(novos, modificados, removidos))

    def _inicio_ui_scan(self):
        self.btn_scan.configure(state='disabled', text="⏳  Escaneando...")
        self.btn_parar.configure(state='normal', text="⏹ Parar")
        self.btn_parar.pack(side='left', padx=(0, 10))
        self.lbl_status.configure(text="🔍 Escaneando... Aguarde.")
        self.lbl_progress.configure(text="Iniciando scan...")
        self.progress_bar.pack(side='left', padx=(8, 0))
        self.progress_bar.start(12)

    def _fim_ui_scan(self):
        self.escaneando = False
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.lbl_progress.configure(text="")
        self.btn_scan.configure(state='normal', text="🔍  Escanear")
        self.btn_parar.pack_forget()

    def _scan_cancelado(self, n_parcial):
        """Chamado na thread principal quando o scan é cancelado pelo usuário."""
        self._fim_ui_scan()
        self.lbl_status.configure(
            text=f"⏹ Scan cancelado. {n_parcial} item(ns) coletados (não salvos)."
        )

    def _pos_scan(self, novos, modificados, removidos):
        lista = self.listas[self.lista_ativa]
        self.carregar_tree(lista)
        self.atualizar_sidebar()
        self.lbl_ultimo_scan.configure(text=f"Último scan: {lista['ultimo_scan']}")

        n = len(lista['itens'])
        self._fim_ui_scan()

        # Atualiza apenas a barra de status com o resumo das mudanças, sem abrir diálogo
        tem_mudancas = novos or modificados or removidos
        if tem_mudancas:
            resumo = []
            if novos: resumo.append(f"{len(novos)} novos")
            if modificados: resumo.append(f"{len(modificados)} modificados")
            if removidos: resumo.append(f"{len(removidos)} removidos")
            
            msg = f"✅ Scan concluído! {n} itens. Mudanças: {', '.join(resumo)}."
            self.lbl_status.configure(text=msg)
        else:
            self.lbl_status.configure(
                text=f"✅ Scan concluído! {n} itens. Nenhuma mudança detectada."
            )

    def _escanear(self, base, max_nivel, incluir_arq):
        """
        Escaneia a pasta base recursivamente até a profundidade max_nivel usando os.walk.
        """
        resultado = []
        cont = 0
        base_abs = os.path.abspath(base)
        
        # Conta separadores para calcular profundidade relativa
        base_norm = os.path.normpath(base_abs)
        start_sep_count = base_norm.count(os.sep)

        try:
            for root, dirs, files in os.walk(base_norm):
                # Verificar cancelamento a cada diretório
                if self._parar_scan.is_set():
                    break

                # Calcula profundidade atual relativa à base
                root_norm = os.path.normpath(root)
                current_depth = root_norm.count(os.sep) - start_sep_count

                # Se atingiu o limite de profundidade, não processa este nível nem desce mais
                if current_depth >= max_nivel:
                    dirs[:] = []  # Impede os.walk de descer mais
                    continue

                # Processar subpastas encontradas neste nível
                for d in sorted(dirs, key=lambda s: s.lower()):
                    if cont >= MAX_ITENS: break
                    
                    full_path = os.path.join(root, d)
                    try:
                        stat = os.stat(full_path)
                        rel_path = os.path.relpath(full_path, base_norm)
                        
                        icone_p = self.icones.get('pasta', '📁')
                        
                        resultado.append({
                            'tipo_id':     'pasta',
                            'tipo':        f'{icone_p} Pasta',
                            'nome':        d,
                            'caminho':     rel_path,
                            'caminho_abs': full_path,
                            'criacao':     fmt_data(stat.st_ctime),
                            'modificacao': fmt_data(stat.st_mtime),
                            'mod_ts':      stat.st_mtime, # Timestamp para filtro
                        })
                        cont += 1
                        
                        if cont % 200 == 0:
                            self.root.after(0, lambda n=cont: self.lbl_progress.configure(
                                text=f"🔍 {n} itens encontrados..."
                            ))
                    except (OSError, PermissionError):
                        continue

                # Processar arquivos se habilitado
                if incluir_arq:
                    for f in sorted(files, key=lambda s: s.lower()):
                        if cont >= MAX_ITENS: break
                        
                        full_path = os.path.join(root, f)
                        try:
                            stat = os.stat(full_path)
                            rel_path = os.path.relpath(full_path, base_norm)
                            ext_full = os.path.splitext(f)[1].lower()
                            ext_clean = ext_full[1:] if ext_full else ""
                            
                            # Buscar ícone: 1. Imagem na pasta, 2. Emoji no JSON, 3. Padrão
                            icone_f = self.icones.get(ext_clean, self.icones.get('arquivo', '📄'))
                            tipo = f"{icone_f} {ext_clean.upper()}" if ext_clean else f"{icone_f} Arq"
                            
                            resultado.append({
                                'tipo_id':     ext_clean if ext_clean else 'arquivo',
                                'tipo':        tipo,
                                'nome':        f,
                                'caminho':     rel_path,
                                'caminho_abs': full_path,
                                'criacao':     fmt_data(stat.st_ctime),
                                'modificacao': fmt_data(stat.st_mtime),
                                'mod_ts':      stat.st_mtime, # Timestamp para filtro
                                'tamanho':     stat.st_size,
                            })
                            cont += 1
                        except (OSError, PermissionError):
                            continue

                if cont >= MAX_ITENS:
                    break

        except Exception as e:
            print(f"Erro no scan: {e}")

        return resultado

    # ══════════════════════════════════════════════════════════════════════
    # EVENTOS DA TREEVIEW
    # ══════════════════════════════════════════════════════════════════════
    def _clique_simples(self, event):
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if col == '#1' and row:       # Clicou na coluna ⭐
            self.toggle_favorito(row)

    def _duplo_clique(self, event):
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if not row or col == '#1':
            return
        self._abrir_item(row)

    def _menu_contexto(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self._row_ctx = row
        try:
            self.ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.ctx_menu.grab_release()

    def _ctx_abrir(self):
        if self._row_ctx:
            self._abrir_item(self._row_ctx)

    def _ctx_favoritar(self):
        if self._row_ctx:
            self.toggle_favorito(self._row_ctx)

    def _ctx_copiar_caminho(self):
        if not self._row_ctx:
            return
        vals = self.tree.item(self._row_ctx)['values']
        if vals:
            self.root.clipboard_clear()
            self.root.clipboard_append(vals[3])

    def _ctx_copiar_nome(self):
        if not self._row_ctx:
            return
        vals = self.tree.item(self._row_ctx)['values']
        if vals:
            self.root.clipboard_clear()
            self.root.clipboard_append(vals[2])

    def _abrir_item(self, row_id):
        if not self.lista_ativa:
            return
        vals = self.tree.item(row_id)['values']
        if not vals:
            return
        cam_rel = vals[3]
        lista   = self.listas[self.lista_ativa]
        # Procurar caminho absoluto
        for item in lista.get('itens', []):
            if item['caminho'] == cam_rel:
                cam_abs = item.get('caminho_abs', '')
                if cam_abs:
                    abrir_no_explorador(cam_abs)
                    return
        # Fallback: montar a partir da pasta base
        pasta_base = lista.get('pasta_base', '')
        cam_abs = os.path.join(pasta_base, cam_rel) if pasta_base else cam_rel
        abrir_no_explorador(cam_abs)

    def toggle_favorito(self, row_id):
        if not self.lista_ativa:
            return
        vals    = self.tree.item(row_id)['values']
        caminho = vals[3]
        lista   = self.listas[self.lista_ativa]
        favs    = lista.get('favoritos', [])

        if caminho in favs:
            favs.remove(caminho)
            is_fav = False
        else:
            favs.append(caminho)
            is_fav = True

        lista['favoritos'] = favs
        self.salvar_dados()

        # Atualizar linha
        novos_vals    = list(vals)
        novos_vals[0] = "⭐" if is_fav else "☆"
        self.tree.item(row_id, values=novos_vals, tags=('favorito',) if is_fav else ())

        # Se estiver na aba favoritos e desfavoritou, remover linha
        if self.aba_ativa == "favoritos" and not is_fav:
            self.tree.delete(row_id)

        # Atualizar contagem e sidebar
        n_itens = len(lista.get('itens', []))
        n_favs  = len(favs)
        self.lbl_contagem.configure(
            text=f"{n_itens} item(ns)  •  ⭐ {n_favs}"
        )
        self.atualizar_sidebar()

    # ══════════════════════════════════════════════════════════════════════
    # EXPORTAR CSV
    # ══════════════════════════════════════════════════════════════════════
    def exportar_csv(self):
        if not self.tree.get_children():
            messagebox.showwarning("Aviso", "Nenhum dado para exportar.", parent=self.root)
            return

        nome_lista = ""
        if self.lista_ativa:
            nome_lista = self.listas[self.lista_ativa]['nome']

        arquivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Todos os arquivos", "*.*")],
            title="Exportar dados como CSV",
            initialfile=f"{nome_lista}_export.csv",
            parent=self.root
        )
        if not arquivo:
            return

        try:
            with open(arquivo, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Favorito', 'Tipo', 'Nome', 'Caminho',
                                 'Data de Criação', 'Última Modificação'])
                for rid in self.tree.get_children():
                    vals = self.tree.item(rid)['values']
                    writer.writerow([
                        'Sim' if vals[0] == '⭐' else 'Não',
                        vals[1], vals[2], vals[3], vals[4], vals[5]
                    ])
            messagebox.showinfo("Sucesso", f"Dados exportados para:\n{arquivo}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar:\n{e}", parent=self.root)

    # ══════════════════════════════════════════════════════════════════════
    # AJUDA / CONFIGURAÇÕES
    # ══════════════════════════════════════════════════════════════════════
    def _mostrar_ajuda(self):
        texto = (
            f"{APP_NAME} v{APP_VERSION}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 COMO USAR:\n"
            "  1. Clique em ＋ na sidebar para criar uma lista.\n"
            "  2. Informe a pasta base (ex: Google Drive).\n"
            "  3. Ajuste a profundidade de varredura.\n"
            "  4. Clique em 🔍 Escanear.\n\n"
            "⭐ FAVORITOS:\n"
            "  • Clique na coluna ★ para favoritar/desfavoritar.\n"
            "  • Use a aba ⭐ Favoritos para ver só eles.\n\n"
            "📂 ÍCONES PERSONALIZADOS:\n"
            "  • Clique em ⚙️ para mapear extensões a emojis.\n"
            "  • Ou coloque imagens .png na pasta 'icones_app'\n"
            "    com o nome da extensão (ex: pdf.png).\n\n"
            "🖱️ MENU DE CONTEXTO:\n"
            "  • Clique direito para opções adicionais.\n"
        )
        win = customtkinter.CTkToplevel(self.root)
        win.title("Ajuda")
        win.geometry("450x580")
        win.attributes("-topmost", True)
        
        customtkinter.CTkLabel(
            win, text=texto,
            font=("Segoe UI", 11),
            justify='left', anchor='nw',
            padx=30, pady=30
        ).pack(fill='both', expand=True)

        customtkinter.CTkButton(
            win, text="Fechar",
            width=120, height=35,
            command=win.destroy
        ).pack(pady=(0, 20))

    def abrir_configuracoes(self):
        win = customtkinter.CTkToplevel(self.root)
        win.title("Configurações de Ícones")
        win.geometry("500x600")
        win.attributes("-topmost", True)

        t = self.tema
        win.configure(fg_color=t['bg'])

        lbl = customtkinter.CTkLabel(win, text="Mapeamento de Ícones (Emojis)", font=("Segoe UI", 16, "bold"))
        lbl.pack(pady=20)

        # Container com scroll para a lista de extensões
        frame_scroll = customtkinter.CTkScrollableFrame(win, width=450, height=400)
        frame_scroll.pack(padx=20, pady=10, fill='both', expand=True)

        self.entries_icones = {} # {ext: entry}

        def adicionar_linha(ext, icone):
            row = customtkinter.CTkFrame(frame_scroll, fg_color="transparent")
            row.pack(fill='x', pady=2)
            
            customtkinter.CTkLabel(row, text=f".{ext}", width=80, anchor='w').pack(side='left', padx=5)
            ent = customtkinter.CTkEntry(row, width=60)
            ent.insert(0, icone)
            ent.pack(side='left', padx=5)
            self.entries_icones[ext] = ent

        # Adicionar os atuais
        for ext in sorted(self.icones.keys()):
            adicionar_linha(ext, self.icones[ext])

        def salvar():
            for ext, ent in self.entries_icones.items():
                self.icones[ext] = ent.get().strip()
            
            # Adicionar nova extensão se preenchida
            nova_ext = entry_nova_ext.get().strip().replace('.', '')
            novo_ico = entry_novo_ico.get().strip()
            if nova_ext and novo_ico:
                self.icones[nova_ext] = novo_ico
            
            self.salvar_dados()
            messagebox.showinfo("Sucesso", "Configurações salvas! Escaneie novamente para aplicar.", parent=win)
            win.destroy()

        # Adicionar nova
        frame_nova = customtkinter.CTkFrame(win, fg_color="transparent")
        frame_nova.pack(pady=10)
        
        customtkinter.CTkLabel(frame_nova, text="Nova Ext:").pack(side='left', padx=5)
        entry_nova_ext = customtkinter.CTkEntry(frame_nova, width=60, placeholder_text="zip")
        entry_nova_ext.pack(side='left', padx=5)
        
        customtkinter.CTkLabel(frame_nova, text="Ícone:").pack(side='left', padx=5)
        entry_novo_ico = customtkinter.CTkEntry(frame_nova, width=60, placeholder_text="📦")
        entry_novo_ico.pack(side='left', padx=5)

        btn_salvar = customtkinter.CTkButton(win, text="Salvar Configurações", command=salvar)
        btn_salvar.pack(pady=20)

    def _abrir_item(self, row_id):
        if not self.lista_ativa:
            return
        vals = self.tree.item(row_id)['values']
        if not vals:
            return
        cam_rel = vals[3]
        lista   = self.listas[self.lista_ativa]
        # Procurar caminho absoluto
        for item in lista.get('itens', []):
            if item['caminho'] == cam_rel:
                cam_abs = item.get('caminho_abs', '')
                if cam_abs:
                    abrir_no_explorador(cam_abs)
                    return
        # Fallback: montar a partir da pasta base
        pasta_base = lista.get('pasta_base', '')
        cam_abs = os.path.join(pasta_base, cam_rel) if pasta_base else cam_rel
        abrir_no_explorador(cam_abs)

    def toggle_favorito(self, row_id):
        if not self.lista_ativa:
            return
        vals    = self.tree.item(row_id)['values']
        caminho = vals[3]
        lista   = self.listas[self.lista_ativa]
        favs    = lista.get('favoritos', [])

        if caminho in favs:
            favs.remove(caminho)
            is_fav = False
        else:
            favs.append(caminho)
            is_fav = True

        lista['favoritos'] = favs
        self.salvar_dados()

        # Atualizar linha
        novos_vals    = list(vals)
        novos_vals[0] = "⭐" if is_fav else "☆"
        self.tree.item(row_id, values=novos_vals, tags=('favorito',) if is_fav else ())

        # Se estiver na aba favoritos e desfavoritou, remover linha
        if self.aba_ativa == "favoritos" and not is_fav:
            self.tree.delete(row_id)

        # Atualizar contagem e sidebar
        n_itens = len(lista.get('itens', []))
        n_favs  = len(favs)
        self.lbl_contagem.configure(
            text=f"{n_itens} item(ns)  •  ⭐ {n_favs}"
        )
        self.atualizar_sidebar()

    # ══════════════════════════════════════════════════════════════════════
    # EXPORTAR CSV
    # ══════════════════════════════════════════════════════════════════════
    def exportar_csv(self):
        if not self.tree.get_children():
            messagebox.showwarning("Aviso", "Nenhum dado para exportar.", parent=self.root)
            return

        nome_lista = ""
        if self.lista_ativa:
            nome_lista = self.listas[self.lista_ativa]['nome']

        arquivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Todos os arquivos", "*.*")],
            title="Exportar dados como CSV",
            initialfile=f"{nome_lista}_export.csv",
            parent=self.root
        )
        if not arquivo:
            return

        try:
            with open(arquivo, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Favorito', 'Tipo', 'Nome', 'Caminho',
                                 'Data de Criação', 'Última Modificação'])
                for rid in self.tree.get_children():
                    vals = self.tree.item(rid)['values']
                    writer.writerow([
                        'Sim' if vals[0] == '⭐' else 'Não',
                        vals[1], vals[2], vals[3], vals[4], vals[5]
                    ])
            messagebox.showinfo("Sucesso", f"Dados exportados para:\n{arquivo}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar:\n{e}", parent=self.root)

    # ══════════════════════════════════════════════════════════════════════
    # AJUDA
    # ══════════════════════════════════════════════════════════════════════
    def _mostrar_ajuda(self):
        texto = (
            f"{APP_NAME} v{APP_VERSION}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 COMO USAR:\n"
            "  1. Clique em ＋ na sidebar para criar uma lista.\n"
            "  2. Informe a pasta base (ex: Google Drive).\n"
            "  3. Ajuste a profundidade de varredura.\n"
            "  4. Clique em 🔍 Escanear.\n\n"
            "★ FAVORITOS:\n"
            "  • Clique na coluna ★ para favoritar/desfavoritar.\n"
            "  • Linhas favoritas ficam em verde.\n"
            "  • Use a aba ⭐ Favoritos para ver só eles.\n\n"
            "📂 ABRIR PASTA:\n"
            "  • Duplo-clique em qualquer item para abri-lo\n"
            "    no explorador de arquivos.\n\n"
            "🖱️ MENU DE CONTEXTO:\n"
            "  • Clique direito para opções adicionais.\n"
            "📤 EXPORTAR:\n"
            "  • Clique em Exportar CSV para salvar a lista atual.\n"
            "🔄 MÚLTIPLAS LISTAS:\n"
            "  • Crie listas com pastas diferentes.\n"
        )
        win = customtkinter.CTkToplevel(self.root)
        win.title("Ajuda")
        win.geometry("450x520")
        win.attributes("-topmost", True)
        
        customtkinter.CTkLabel(
            win, text=texto,
            font=("Segoe UI", 11),
            justify='left', anchor='nw',
            padx=30, pady=30
        ).pack(fill='both', expand=True)

        customtkinter.CTkButton(
            win, text="Fechar",
            width=120, height=35,
            command=win.destroy
        ).pack(pady=(0, 20))


# ══════════════════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Necessário para executáveis PyInstaller com multiprocessing --
    # impede que processos filhos reiniciem o app em loop infinito.
    multiprocessing.freeze_support()

    # ── Instância única (Windows Named Mutex) ────────────────────────────────
    # Garante que apenas UMA cópia do app rode por vez.
    _MUTEX_NAME = "Global\\MonitorAtualizacoes_SingleInstance"
    _mutex = None
    try:
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        _last_error = ctypes.windll.kernel32.GetLastError()
        if _last_error == 183:  # ERROR_ALREADY_EXISTS
            import tkinter as _tk
            import tkinter.messagebox as _mb
            _r = _tk.Tk()
            _r.withdraw()
            _mb.showwarning(
                "Monitor de Atualizações",
                "O aplicativo já está em execução.\n"
                "Verifique a barra de tarefas."
            )
            _r.destroy()
            sys.exit(0)
    except Exception:
        pass  # Se falhar (ex: não-Windows), apenas continua normalmente

    # DPI awareness no Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = customtkinter.CTk()
    app = MonitorApp(root)
    root.mainloop()

    # Libera o mutex ao encerrar
    if _mutex:
        try:
            ctypes.windll.kernel32.ReleaseMutex(_mutex)
            ctypes.windll.kernel32.CloseHandle(_mutex)
        except Exception:
            pass
