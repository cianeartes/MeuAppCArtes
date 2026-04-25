# Colagem Inteligente
import os
import math
import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES
from PIL import Image, ImageOps, ImageTk, ImageDraw

import platform
import subprocess
import shutil
import json
import threading
from tkinter import colorchooser, filedialog
import copy
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageEnhance, ImageOps

_appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
_config_dir = os.path.join(_appdata, 'ColagemInteligente')
os.makedirs(_config_dir, exist_ok=True)
CONFIG_FILE = os.path.join(_config_dir, 'config.json')

def carregar_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def salvar_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception:
        pass

def mover_para_lixeira(path):
    """Move para lixeira do SO sem dependências externas."""
    path = os.path.abspath(path)
    sistema = platform.system()

    if sistema == 'Windows':
        import ctypes
        from ctypes import wintypes
        class SHFILEOPSTRUCT(ctypes.Structure):
            _fields_ = [
                ('hwnd',                  wintypes.HWND),
                ('wFunc',                 wintypes.UINT),
                ('pFrom',                 wintypes.LPCWSTR),
                ('pTo',                   wintypes.LPCWSTR),
                ('fFlags',                wintypes.WORD),
                ('fAnyOperationsAborted', wintypes.BOOL),
                ('hNameMappings',         ctypes.c_void_p),
                ('lpszProgressTitle',     wintypes.LPCWSTR),
            ]
        FO_DELETE = 0x0003
        FOF_FLAGS = 0x0040 | 0x0010 | 0x0400 | 0x0004  # ALLOWUNDO | NOCONFIRM | NOERRORUI | SILENT
        op = SHFILEOPSTRUCT()
        op.wFunc  = FO_DELETE
        op.pFrom  = path + '\0\0'
        op.fFlags = FOF_FLAGS
        ret = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        if ret != 0:
            raise OSError(f'SHFileOperation falhou: {ret}')

    elif sistema == 'Darwin':
        script = f'tell application "Finder" to delete POSIX file "{path}"'
        ret = subprocess.call(['osascript', '-e', script],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ret != 0:
            raise OSError('osascript falhou')

    else:
        # Linux: tenta gio, kioclient, trash-cli, depois XDG manual
        for cmd in (['gio', 'trash', path],
                    ['kioclient5', 'move', path, 'trash:/'],
                    ['kioclient',  'move', path, 'trash:/'],
                    ['trash-put',  path]):
            try:
                if subprocess.call(cmd, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL) == 0:
                    return
            except FileNotFoundError:
                continue
        # Fallback XDG manual
        xdg_trash = os.path.join(
            os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share')),
            'Trash', 'files')
        os.makedirs(xdg_trash, exist_ok=True)
        base, ext = os.path.splitext(os.path.basename(path))
        dest = os.path.join(xdg_trash, os.path.basename(path))
        i = 1
        while os.path.exists(dest):
            dest = os.path.join(xdg_trash, f'{base}_{i}{ext}')
            i += 1
        shutil.move(path, dest)

# ═══════════════════════════════════════════════════════════════
def montar_colagem_interface(parent, session_in=None):
    for widget in parent.winfo_children():
        widget.destroy()

    cfg = carregar_config()
    is_dark = cfg.get('is_dark', True)

    TEMA_DARK = {
        'bg_main':    '#0F172A',
        'bg_panel':   '#1E293B',
        'bg_drop':    '#1E293B',
        'accent':     '#6366F1',
        'accent_hi':  '#818CF8',
        'text_main':  '#F8FAFC',
        'text_sec':   '#94A3B8',
        'font_main':  ('Segoe UI', 10),
        'font_title': ('Segoe UI', 11, 'bold'),
        'font_small': ('Segoe UI', 9),
    }

    TEMA_LIGHT = {
        'bg_main':    '#F8FAFC',
        'bg_panel':   '#F1F5F9',
        'bg_drop':    '#E2E8F0',
        'accent':     '#4F46E5',
        'accent_hi':  '#6366F1',
        'text_main':  '#0F172A',
        'text_sec':   '#475569',
        'font_main':  ('Segoe UI', 10),
        'font_title': ('Segoe UI', 11, 'bold'),
        'font_small': ('Segoe UI', 9),
    }

    TEMA = TEMA_DARK if is_dark else TEMA_LIGHT

    # Configuração de Estilo Global (ttk)
    style = ttk.Style()
    if 'clam' in style.theme_names():
        style.theme_use('clam')
    
    style.configure('TButton', font=TEMA['font_main'], background=TEMA['bg_panel'],
                    foreground=TEMA['text_main'], borderwidth=0, lightcolor=TEMA['bg_panel'],
                    darkcolor=TEMA['bg_panel'], bordercolor=TEMA['bg_main'], padding=6)
    style.map('TButton', background=[('active', TEMA['accent'])], foreground=[('active', TEMA['text_main'])])

    parent.config(bg=TEMA['bg_main'])

    if session_in is None:
        session = {
            'images':         [],
            'batch_size':     4,
            'last_folder':    None,
            'icones_refs':    [],
            'icones_widgets': {},
            'icones_paths':   {},
            'lote_states':    {},
            'status_msg':     '',
            'auto_colagem':   cfg.get('auto_colagem', False),
            'auto_settings':  cfg.get('auto_settings', {
                'gap': 0, 'radius': 0, 'bg_color': '#FFFFFF',
                'aspect_ratio': None, 'template': 'grade', 'bg_image': None
            }),
        }
    else:
        session = session_in
        session['icones_refs'] = []
        session['icones_widgets'] = {}

    def set_status(msg):
        session['status_msg'] = msg
        status_var.set(msg)

    # ── Utilitários ────────────────────────────────────────────

    def gerar_nome_unico(folder, base='colagem_final', ext='.jpg'):
        c = os.path.join(folder, base + ext)
        if not os.path.exists(c):
            return c
        i = 1
        while True:
            c = os.path.join(folder, f'{base}_{i}{ext}')
            if not os.path.exists(c):
                return c
            i += 1

    def abrir_imagem(img_path):
        img = Image.open(img_path)
        img = ImageOps.exif_transpose(img)
        if img.mode in ('RGBA', 'LA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            return bg
        return img.convert('RGB')

    def escolher_layout(qtd):
        layouts = {
            1:(1,1), 2:(1,2), 3:(1,3), 4:(2,2),
            5:(2,3), 6:(2,3), 7:(3,3), 8:(3,3),
            9:(3,3), 10:(3,4), 11:(3,4), 12:(3,4),
        }
        if qtd in layouts:
            return layouts[qtd]
        cols = math.ceil(math.sqrt(qtd))
        return math.ceil(qtd / cols), cols

    def resize_fit(img, box_w, box_h, ox=0.0, oy=0.0, zoom=1.0):
        """
        Preenche box_w x box_h com crop.
        ox/oy  : offset em -1..1  (0 = centro)
        zoom   : 1.0 = padrão, >1 aproxima, <1 afasta.
        """
        if box_w < 1 or box_h < 1:
            return Image.new('RGB', (max(1,box_w), max(1,box_h)), (200,200,200))

        if zoom >= 1.0:
            scale_w = box_w / img.width
            scale_h = box_h / img.height
            scale = max(scale_w, scale_h) * zoom
            
            nw = max(1, int(img.width * scale))
            nh = max(1, int(img.height * scale))
            
            resized = img.resize((nw, nh), Image.LANCZOS)
            
            sx = nw - box_w
            sy = nh - box_h
            
            left = int(sx/2 + ox * sx/2)
            top  = int(sy/2 + oy * sy/2)
            
            left = max(0, min(left, sx))
            top  = max(0, min(top, sy))
            
            return resized.crop((left, top, left + box_w, top + box_h))
        else:
            scale_w = box_w / img.width
            scale_h = box_h / img.height
            scale = min(scale_w, scale_h) * zoom
            
            nw = max(1, int(img.width * scale))
            nh = max(1, int(img.height * scale))
            
            resized = img.resize((nw, nh), Image.LANCZOS)
            
            sx = box_w - nw
            sy = box_h - nh
            
            paste_x = int(sx/2 + ox * sx/2)
            paste_y = int(sy/2 + oy * sy/2)
            
            paste_x = max(0, min(paste_x, sx))
            paste_y = max(0, min(paste_y, sy))
            
            result = Image.new('RGB', (box_w, box_h), (255, 255, 255))
            result.paste(resized, (paste_x, paste_y))
            return result

    # ── Geração do arquivo final ────────────────────────────────

    def gerar_nome_unico(pasta, base="colagem", ext=".jpg"):
        idx = 1
        while True:
            nome = f"{base}_{idx}{ext}"
            caminho = os.path.join(pasta, nome)
            if not os.path.exists(caminho):
                return caminho
            idx += 1

    def process_image_fx(img, transform, filt):
        if transform['flip_h']: img = ImageOps.mirror(img)
        if transform['flip_v']: img = ImageOps.flip(img)
        if transform['rotate'] != 0: 
            img = img.rotate(transform['rotate'], expand=True)
            
        ftype = filt['type']
        if ftype == 'pb':
            img = ImageOps.grayscale(img).convert('RGB')
        elif ftype == 'sepia':
            gray = ImageOps.grayscale(img)
            img = ImageOps.colorize(gray, "#000000", "#ffeedd").convert('RGB')
            
        b = filt['brightness']
        if b != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(b)
            
        return img

    def calc_cell_rects(tw, th, qtd, cols, state, gap_real):
        t = state.get('template', 'grade')
        rects = []
        g = gap_real
        
        uw = tw - 2 * g
        uh = th - 2 * g
        if uw < 1: uw = 1
        if uh < 1: uh = 1
        
        if t == 'grade':
            rows_count = len(state['row_frac'])
            image_area_w = tw - (cols + 1) * g
            image_area_h = th - (rows_count + 1) * g
            if image_area_w < 1: image_area_w = 1
            if image_area_h < 1: image_area_h = 1
            
            col_ws = [int(f * image_area_w) for f in state['col_frac']]
            row_hs = [int(f * image_area_h) for f in state['row_frac']]
            col_ws[-1] = image_area_w - sum(col_ws[:-1])
            row_hs[-1] = image_area_h - sum(row_hs[:-1])
            
            col_xs, x = [], g
            for ci in range(cols):
                col_xs.append(x); x += col_ws[ci] + g
            row_ys, y = [], g
            for ri in range(len(row_hs)):
                row_ys.append(y); y += row_hs[ri] + g
                
            for i in range(qtd):
                ri = i // cols; ci = i % cols
                rects.append((col_xs[ci], row_ys[ri], col_ws[ci], row_hs[ri]))
                
        elif t == 'hero_left':
            if qtd <= 1:
                rects.append((g, g, uw, uh))
            else:
                hero_w = (uw - g) // 2
                rects.append((g, g, hero_w, uh))
                right_w = uw - hero_w - g
                right_h_total = uh - g * (qtd - 2)
                cell_h = right_h_total // (qtd - 1)
                rx = g + hero_w + g
                ry = g
                for i in range(1, qtd):
                    h = cell_h if i < qtd - 1 else (uh - (ry - g))
                    rects.append((rx, ry, right_w, h))
                    ry += h + g
                    
        elif t == 'hero_top':
            if qtd <= 1:
                rects.append((g, g, uw, uh))
            else:
                hero_h = (uh - g) // 2
                rects.append((g, g, uw, hero_h))
                bot_h = uh - hero_h - g
                bot_w_total = uw - g * (qtd - 2)
                cell_w = bot_w_total // (qtd - 1)
                bx = g
                by = g + hero_h + g
                for i in range(1, qtd):
                    w = cell_w if i < qtd - 1 else (uw - (bx - g))
                    rects.append((bx, by, w, bot_h))
                    bx += w + g
                    
        elif t == 'hero_right':
            if qtd <= 1:
                rects.append((g, g, uw, uh))
            else:
                hero_w = (uw - g) // 2
                rects.append((g + (uw - hero_w), g, hero_w, uh))
                left_w = uw - hero_w - g
                left_h_total = uh - g * (qtd - 2)
                cell_h = left_h_total // (qtd - 1)
                lx = g
                ly = g
                for i in range(1, qtd):
                    h = cell_h if i < qtd - 1 else (uh - (ly - g))
                    rects.append((lx, ly, left_w, h))
                    ly += h + g

        elif t == 'hero_bottom':
            if qtd <= 1:
                rects.append((g, g, uw, uh))
            else:
                hero_h = (uh - g) // 2
                rects.append((g, g + (uh - hero_h), uw, hero_h))
                top_h = uh - hero_h - g
                top_w_total = uw - g * (qtd - 2)
                cell_w = top_w_total // (qtd - 1)
                tx = g
                ty = g
                for i in range(1, qtd):
                    w = cell_w if i < qtd - 1 else (uw - (tx - g))
                    rects.append((tx, ty, w, top_h))
                    tx += w + g

        elif t == 'coluna':
            cell_h_total = uh - g * (qtd - 1)
            cell_h = cell_h_total // qtd
            y = g
            for i in range(qtd):
                h = cell_h if i < qtd - 1 else (uh - (y - g))
                rects.append((g, y, uw, h))
                y += h + g

        elif t == 'linha':
            cell_w_total = uw - g * (qtd - 1)
            cell_w = cell_w_total // qtd
            x = g
            for i in range(qtd):
                w = cell_w if i < qtd - 1 else (uw - (x - g))
                rects.append((x, g, w, uh))
                x += w + g
                    
        return rects

    def make_collage(image_paths, output_path, state, gap_real):
        qtd = len(image_paths)
        rows, cols = escolher_layout(qtd)
        imagens = [abrir_imagem(p) for p in image_paths]

        avg_w = int(sum(img.width  for img in imagens) / len(imagens))
        avg_h = int(sum(img.height for img in imagens) / len(imagens))
        total_w = avg_w * cols
        total_h = avg_h * rows

        ar = state.get('aspect_ratio')
        if ar:
            if total_w / total_h > ar:
                total_h = int(total_w / ar)
            else:
                total_w = int(total_h * ar)

        col_ws = [int(f * total_w) for f in state['col_frac']]
        row_hs = [int(f * total_h) for f in state['row_frac']]
        col_ws[-1] = total_w - sum(col_ws[:-1])
        row_hs[-1] = total_h - sum(row_hs[:-1])

        cw = total_w + gap_real * (cols + 1)
        ch = total_h + gap_real * (rows + 1)
        
        bg_img_path = state.get('bg_image')
        if bg_img_path and os.path.exists(bg_img_path):
            try:
                bg_orig = Image.open(bg_img_path).convert('RGB')
                collage = ImageOps.fit(bg_orig, (cw, ch), centering=(0.5, 0.5))
            except:
                collage = Image.new('RGB', (cw, ch), state.get('bg_color', '#FFFFFF'))
        else:
            collage = Image.new('RGB', (cw, ch), state.get('bg_color', '#FFFFFF'))

        rects = calc_cell_rects(cw, ch, qtd, cols, state, gap_real)
        for idx, img in enumerate(imagens):
            rx, ry, rw, rh = rects[idx]
            ox, oy = state['offsets'].get(idx, (0.0, 0.0))
            z = state['zooms'].get(idx, 1.0)
            
            img_fx = process_image_fx(img, state['transforms'][idx], state['filters'][idx])
            fitted = resize_fit(img_fx, rw, rh, ox, oy, z)
            
            rad = state.get('radius', 0)
            if rad > 0:
                mask = Image.new('L', fitted.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, rw, rh), radius=rad, fill=255)
                collage.paste(fitted, (rx, ry), mask)
            else:
                collage.paste(fitted, (rx, ry))

        wm = carregar_config().get('watermark', '').strip()
        if wm:
            try:
                draw = ImageDraw.Draw(collage)
                try: font = ImageFont.truetype("arial.ttf", size=max(20, int(total_w * 0.02)))
                except: font = ImageFont.load_default()
                bbox = font.getbbox(wm)
                tw_t, th_t = bbox[2] - bbox[0], bbox[3] - bbox[1]
                margin = max(10, int(total_w * 0.01))
                x_t, y_t = collage.width - tw_t - margin, collage.height - th_t - margin
                draw.text((x_t+2, y_t+2), wm, fill=(0,0,0), font=font)
                draw.text((x_t, y_t), wm, fill=(255,255,255), font=font)
            except Exception as e:
                pass

        cfg = carregar_config()
        q = cfg.get('jpeg_quality', 95)
        fmt = cfg.get('output_format', '.jpg').lower()
        
        if fmt in ('.jpg', '.jpeg'):
            collage.save(output_path, 'JPEG', quality=q)
        elif fmt == '.webp':
            collage.save(output_path, 'WEBP', quality=q)
        else:
            collage.save(output_path, 'PNG')

    # ── Preview / edição interativa ────────────────────────────

    def abrir_preview(image_paths_in, lote_idx):
        # lista mutável de caminhos (permite troca de foto por drop)
        img_paths = list(image_paths_in)
        qtd = len(img_paths)
        rows, cols = escolher_layout(qtd)

        # cache de imagens abertas (recriado ao trocar foto)
        imagens_orig = [abrir_imagem(p) for p in img_paths]

        avg_w = int(sum(img.width  for img in imagens_orig) / len(imagens_orig))
        avg_h = int(sum(img.height for img in imagens_orig) / len(imagens_orig))

        # Tentar recuperar o estado salvo anterior (se os arquivos forem os mesmos)
        saved = session['lote_states'].get(lote_idx)
        is_new_collage = not (saved and saved.get('img_paths') == img_paths)
        
        if not is_new_collage:
            state = {
                'offsets':  saved.get('offsets', {i: (0.0, 0.0) for i in range(qtd)}).copy(),
                'col_frac': saved.get('col_frac', [1.0/cols] * cols).copy(),
                'row_frac': saved.get('row_frac', [1.0/rows] * rows).copy(),
                'gap':      saved.get('gap', 0),
                'zooms':    saved.get('zooms', {i: 1.0 for i in range(qtd)}).copy(),
                'bg_color': saved.get('bg_color', carregar_config().get('bg_color', '#FFFFFF')),
                'aspect_ratio': saved.get('aspect_ratio'),
                'transforms': saved.get('transforms', {i: {'rotate': 0, 'flip_h': False, 'flip_v': False} for i in range(qtd)}).copy(),
                'filters': saved.get('filters', {i: {'type': 'normal', 'brightness': 1.0} for i in range(qtd)}).copy(),
                'radius': saved.get('radius', 0),
                'template': saved.get('template', 'grade'),
                'bg_image': saved.get('bg_image', None),
            }
        else:
            state = {
                'offsets':  {i: (0.0, 0.0) for i in range(qtd)},
                'col_frac': [1.0/cols] * cols,
                'row_frac': [1.0/rows] * rows,
                'gap':      0,
                'zooms':    {i: 1.0 for i in range(qtd)},
                'bg_color': carregar_config().get('bg_color', '#FFFFFF'),
                'aspect_ratio': None,
                'transforms': {i: {'rotate': 0, 'flip_h': False, 'flip_v': False} for i in range(qtd)},
                'filters': {i: {'type': 'normal', 'brightness': 1.0} for i in range(qtd)},
                'radius': 0,
                'template': 'grade',
                'bg_image': None,
            }

        win = tk.Toplevel(parent)
        win.title(f'Colagem {lote_idx+1}  ({qtd} foto{"s" if qtd>1 else ""})')
        win.configure(bg=TEMA['bg_main'])
        win.geometry('900x700')
        win.resizable(True, True)

        parent.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()  - 900) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 700) // 2
        win.geometry(f'+{max(0, px)}+{max(0, py)}')

        history = []
        var_recolocar = tk.BooleanVar(value=False)
        
        def salvar_estado():
            history.append(copy.deepcopy(state))
            if len(history) > 20: history.pop(0)

        def atualizar_preview():
            w = canvas_frame.winfo_width()
            h = canvas_frame.winfo_height()
            if w > 10 and h > 10:
                recalcular_tamanho_preview(w, h)
                redesenhar()

        def desfazer(event=None):
            if history:
                state.clear()
                state.update(history.pop())
                atualizar_preview()
                
        win.bind('<Control-z>', desfazer)

        PW = 0; PH = 0; scale = 1.0
        
        def recalcular_tamanho_preview(avail_w, avail_h):
            nonlocal PW, PH, scale
            base_cw = avg_w * cols
            base_ch = avg_h * rows
            
            ar = state.get('aspect_ratio')
            if ar:
                if base_cw / base_ch > ar:
                    base_ch = int(base_cw / ar)
                else:
                    base_cw = int(base_ch * ar)
            
            total_theo_w = base_cw + state['gap'] * (cols + 1)
            total_theo_h = base_ch + state['gap'] * (rows + 1)
            
            if total_theo_w == 0 or total_theo_h == 0: return
            scale = min(avail_w / total_theo_w, avail_h / total_theo_h, 1.0)
            
            PW = int(base_cw * scale)
            PH = int(base_ch * scale)

        canvas_frame = tk.Frame(win, bg=TEMA['bg_main'])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 0))

        canvas = tk.Canvas(canvas_frame, bg=TEMA['bg_main'], highlightthickness=0)
        canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        def on_canvas_resize(event):
            if event.width > 10 and event.height > 10:
                recalcular_tamanho_preview(event.width, event.height)
                redesenhar()
                
        canvas_frame.bind('<Configure>', on_canvas_resize)

        tk_cells = {}
        DIVIDER_HIT = 8

        # ── Geometria ──

        def get_gap():
            return int(state['gap'] * scale)

        def total_wh():
            g = get_gap()
            return PW + g*(cols+1), PH + g*(rows+1)

        def get_col_widths():  return [int(f * PW) for f in state['col_frac']]
        def get_row_heights(): return [int(f * PH) for f in state['row_frac']]
        
        def get_col_xs():
            g, xs, x = get_gap(), [], get_gap()
            for f in state['col_frac']: xs.append(x);  x += int(f * PW) + g
            return xs
            
        def get_row_ys():
            g, ys, y = get_gap(), [], get_gap()
            for f in state['row_frac']: ys.append(y);  y += int(f * PH) + g
            return ys

        def hit_test(mx, my):
            tw, th = total_wh()
            rects = calc_cell_rects(tw, th, qtd, cols, state, get_gap())
            
            if state.get('template', 'grade') == 'grade':
                g = get_gap()
                xs = get_col_xs(); ys = get_row_ys()
                ws = get_col_widths(); hs = get_row_heights()
                for ci in range(cols-1):
                    divx = xs[ci] + ws[ci] + max(g//2, 1)
                    if abs(mx - divx) <= max(DIVIDER_HIT, g//2+2): return ('vcol', ci)
                for ri in range(rows-1):
                    divy = ys[ri] + hs[ri] + max(g//2, 1)
                    if abs(my - divy) <= max(DIVIDER_HIT, g//2+2): return ('hrow', ri)
            
            for idx, (rx, ry, rw, rh) in enumerate(rects):
                if rx <= mx <= rx+rw and ry <= my <= ry+rh:
                    return ('cell', idx)
            return None

        def cell_at(mx, my):
            tw, th = total_wh()
            rects = calc_cell_rects(tw, th, qtd, cols, state, get_gap())
            for idx, (rx, ry, rw, rh) in enumerate(rects):
                if rx <= mx <= rx+rw and ry <= my <= ry+rh: return idx
            return None

        def redesenhar(hi_cell=None, hi_div=None, hi_drop=None):
            canvas.delete('all')
            tw, th = total_wh()
            canvas.config(width=tw, height=th)
            
            bg_img_path = state.get('bg_image')
            if bg_img_path and os.path.exists(bg_img_path):
                try:
                    bg_orig = Image.open(bg_img_path).convert('RGB')
                    bg_fit = ImageOps.fit(bg_orig, (tw, th), centering=(0.5, 0.5))
                    tk_bg = ImageTk.PhotoImage(bg_fit)
                    tk_cells['bg'] = tk_bg # manter ref
                    canvas.create_image(0, 0, anchor='nw', image=tk_bg)
                except:
                    bg_c = state.get('bg_color', '#FFFFFF')
                    canvas.create_rectangle(0, 0, tw, th, fill=bg_c, outline='')
            else:
                bg_c = state.get('bg_color', '#FFFFFF')
                canvas.create_rectangle(0, 0, tw, th, fill=bg_c, outline='')
            
            rects = calc_cell_rects(tw, th, qtd, cols, state, get_gap())

            for idx, img in enumerate(imagens_orig):
                rx, ry, rw, rh = rects[idx]
                ox, oy = state['offsets'][idx]
                z = state['zooms'][idx]
                
                img_fx = process_image_fx(img, state['transforms'][idx], state['filters'][idx])
                fitted = resize_fit(img_fx, rw, rh, ox, oy, z)
                
                rad = int(state.get('radius', 0) * scale)
                if rad > 0:
                    mask = Image.new('L', fitted.size, 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle((0, 0, rw, rh), radius=rad, fill=255)
                    fitted = fitted.convert('RGBA')
                    fitted.putalpha(mask)
                    
                d = ImageDraw.Draw(fitted)
                if idx == hi_cell:
                    d.rectangle([0,0,rw-1,rh-1], outline=(255,165,0), width=4)
                if idx == hi_drop:
                    d.rectangle([0,0,rw-1,rh-1], outline=(100,220,100), width=6)
                    
                tk_img = ImageTk.PhotoImage(fitted)
                tk_cells[idx] = tk_img
                canvas.create_image(rx, ry, anchor='nw', image=tk_img)

            if state.get('template', 'grade') == 'grade':
                g = get_gap()
                xs = get_col_xs(); ys = get_row_ys()
                ws = get_col_widths(); hs = get_row_heights()
                for ci in range(cols-1):
                    divx = xs[ci]+ws[ci]+max(g//2,1)
                    color = TEMA['accent_hi'] if hi_div==('vcol',ci) else '#334155'
                    lw = 4 if hi_div==('vcol',ci) else 1
                    canvas.create_line(divx, g, divx, th - g, fill=color, width=lw)
                for ri in range(rows-1):
                    divy = ys[ri]+hs[ri]+max(g//2,1)
                    color = TEMA['accent_hi'] if hi_div==('hrow',ri) else '#334155'
                    lw = 4 if hi_div==('hrow',ri) else 1
                    canvas.create_line(g, divy, tw - g, divy, fill=color, width=lw)

        redesenhar()

        # ── Drag state ──

        drag = {'type': None, 'idx': None,
                'x0': 0, 'y0': 0,
                'ox0': 0.0, 'oy0': 0.0,
                'frac0': None}

        def on_motion(event):
            hit = hit_test(event.x, event.y)
            if   hit and hit[0]=='vcol': canvas.config(cursor='sb_h_double_arrow')
            elif hit and hit[0]=='hrow': canvas.config(cursor='sb_v_double_arrow')
            elif hit and hit[0]=='cell': canvas.config(cursor='fleur')
            else:                        canvas.config(cursor='arrow')

        def on_press(event):
            hit = hit_test(event.x, event.y)
            if hit is None:
                drag['type'] = None; return
            salvar_estado()
            kind, val = hit
            drag.update(type=kind, idx=val, x0=event.x, y0=event.y)
            if kind == 'cell':
                ox, oy = state['offsets'].get(val, (0.0, 0.0))
                drag['ox0'] = ox;  drag['oy0'] = oy
                redesenhar(hi_cell=val)
            elif kind in ('vcol','hrow'):
                drag['frac0'] = (state['col_frac'] if kind=='vcol' else state['row_frac'])[:]
                redesenhar(hi_div=(kind, val))

        def on_drag(event):
            kind = drag['type']
            if kind is None: return
            dx = event.x - drag['x0']
            dy = event.y - drag['y0']

            if kind == 'cell':
                idx = drag['idx']
                
                if var_recolocar.get():
                    t_idx = cell_at(event.x, event.y)
                    redesenhar(hi_cell=idx, hi_drop=t_idx)
                    return

                img = imagens_orig[idx]
                ws  = get_col_widths();  hs = get_row_heights()
                ci  = idx%cols;  ri = idx//cols
                pcw = ws[ci];  pch = hs[ri]
                z   = state['zooms'].get(idx, 1.0)
                
                if z >= 1.0:
                    scale_w = pcw / img.width
                    scale_h = pch / img.height
                    scale = max(scale_w, scale_h) * z
                    nw = int(img.width * scale)
                    nh = int(img.height * scale)
                    sx = nw - pcw
                    sy = nh - pch
                    
                    ox = drag['ox0'] - (dx/(sx/2)) if sx > 0 else drag['ox0']
                    oy = drag['oy0'] - (dy/(sy/2)) if sy > 0 else drag['oy0']
                else:
                    scale_w = pcw / img.width
                    scale_h = pch / img.height
                    scale = min(scale_w, scale_h) * z
                    nw = int(img.width * scale)
                    nh = int(img.height * scale)
                    sx = pcw - nw
                    sy = pch - nh
                    
                    ox = drag['ox0'] + (dx/(sx/2)) if sx > 0 else drag['ox0']
                    oy = drag['oy0'] + (dy/(sy/2)) if sy > 0 else drag['oy0']

                state['offsets'][idx] = (max(-1.0,min(1.0,ox)), max(-1.0,min(1.0,oy)))
                redesenhar(hi_cell=idx)

            elif kind == 'vcol':
                ci = drag['idx'];  fracs = drag['frac0'][:]
                df = dx/PW
                na = fracs[ci]+df;  nb = fracs[ci+1]-df
                if na>=0.05 and nb>=0.05:
                    state['col_frac'][ci]=na;  state['col_frac'][ci+1]=nb
                redesenhar(hi_div=('vcol',ci))

            elif kind == 'hrow':
                ri = drag['idx'];  fracs = drag['frac0'][:]
                df = dy/PH
                na = fracs[ri]+df;  nb = fracs[ri+1]-df
                if na>=0.05 and nb>=0.05:
                    state['row_frac'][ri]=na;  state['row_frac'][ri+1]=nb
                redesenhar(hi_div=('hrow',ri))

        def on_release(event):
            if drag['type'] == 'cell':
                if var_recolocar.get() or (event.state & 0x0004):
                    t_idx = cell_at(event.x, event.y)
                    s_idx = drag['idx']
                    if t_idx is not None and t_idx != s_idx:
                        salvar_estado()
                        img_paths[s_idx], img_paths[t_idx] = img_paths[t_idx], img_paths[s_idx]
                        imagens_orig[s_idx], imagens_orig[t_idx] = imagens_orig[t_idx], imagens_orig[s_idx]
                        def sw(k): state[k][s_idx], state[k][t_idx] = state[k][t_idx], state[k][s_idx]
                        sw('offsets'); sw('zooms'); sw('transforms'); sw('filters')
                        redesenhar()
                        drag['type'] = None
                        return
            drag['type'] = None
            redesenhar()

        # ── Scroll = zoom por célula ──

        def on_scroll(event):
            delta = getattr(event, 'delta', 0)
            zoom_in = (event.num == 4 or delta > 0)
            # descobre célula sob o mouse
            idx = cell_at(event.x, event.y)
            if idx is None:
                return
            salvar_estado()
            z = state['zooms'].get(idx, 1.0)
            step = 0.05
            z = z + step if zoom_in else z - step
            z = max(0.3, min(4.0, z))
            state['zooms'][idx] = z
            lbl_zoom.config(text=f'Zoom célula #{idx+1}: {z:.2f}×')
            redesenhar()

        canvas.bind('<Motion>',          on_motion)
        canvas.bind('<ButtonPress-1>',   on_press)
        canvas.bind('<B1-Motion>',       on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        canvas.bind('<MouseWheel>',      on_scroll)
        canvas.bind('<Button-4>',        on_scroll)
        canvas.bind('<Button-5>',        on_scroll)

        # ── Drop de foto em célula específica ──

        def on_cell_drop(event):
            files = win.tk.splitlist(event.data)
            valid = [f for f in files
                     if os.path.isfile(f) and f.lower().endswith(
                         ('.jpg','.jpeg','.png','.bmp','.webp'))]
            if not valid:
                return
            new_path = valid[0]
            # descobre célula pelo cursor (aproximado: centro do canvas como fallback)
            try:
                mx = canvas.winfo_pointerx() - canvas.winfo_rootx()
                my = canvas.winfo_pointery() - canvas.winfo_rooty()
            except Exception:
                mx, my = 0, 0
            idx = cell_at(mx, my)
            if idx is None:
                # se não identificou, coloca na primeira célula
                idx = 0
            salvar_estado()
            img_paths[idx] = new_path
            imagens_orig[idx] = abrir_imagem(new_path)
            state['offsets'][idx] = (0.0, 0.0)
            state['zooms'][idx]   = 1.0
            redesenhar(hi_drop=idx)
            # pisca o highlight por 600ms e volta ao normal
            win.after(600, redesenhar)

        def on_right_click(event):
            idx = cell_at(event.x, event.y)
            if idx is None: return
            
            menu = tk.Menu(win, tearoff=0)
            
            def do_rot(a):
                salvar_estado()
                state['transforms'][idx]['rotate'] = (state['transforms'][idx]['rotate'] + a) % 360
                state['zooms'][idx] = 1.0
                state['offsets'][idx] = (0.0, 0.0)
                redesenhar()
                
            def do_flip(f):
                salvar_estado()
                state['transforms'][idx][f] = not state['transforms'][idx][f]
                redesenhar()
                
            def do_filt(f):
                salvar_estado()
                state['filters'][idx]['type'] = f
                redesenhar()
                
            def do_bright(d):
                salvar_estado()
                state['filters'][idx]['brightness'] += d
                redesenhar()
            
            menu.add_command(label="Rotacionar 90º Dir", command=lambda: do_rot(-90))
            menu.add_command(label="Rotacionar 90º Esq", command=lambda: do_rot(90))
            menu.add_command(label="Espelhar Horizontal", command=lambda: do_flip('flip_h'))
            menu.add_command(label="Espelhar Vertical", command=lambda: do_flip('flip_v'))
            menu.add_separator()
            menu.add_command(label="Filtro: Normal", command=lambda: do_filt('normal'))
            menu.add_command(label="Filtro: P&B", command=lambda: do_filt('pb'))
            menu.add_command(label="Filtro: Sépia", command=lambda: do_filt('sepia'))
            menu.add_separator()
            menu.add_command(label="Brilho +10%", command=lambda: do_bright(0.1))
            menu.add_command(label="Brilho -10%", command=lambda: do_bright(-0.1))
            
            menu.tk_popup(event.x_root, event.y_root)
            
        canvas.bind('<Button-3>', on_right_click)

        canvas.drop_target_register(DND_FILES)
        canvas.dnd_bind('<<Drop>>', on_cell_drop)

        # ── Barra de info ──

        info_frame = tk.Frame(win, bg=TEMA['bg_main'])
        info_frame.pack(fill=tk.X, padx=12, pady=(4,0))

        tk.Label(info_frame,
                 text='🖱 Arrastar foto: reposiciona  •  Linha: redimensiona  •  Scroll: zoom  •  Drop foto na célula: substitui',
                 fg=TEMA['text_sec'], bg=TEMA['bg_main'], font=TEMA['font_small']).pack(side=tk.LEFT)

        lbl_zoom = tk.Label(info_frame, text='',
                            fg=TEMA['accent_hi'], bg=TEMA['bg_main'], font=TEMA['font_small'])
        lbl_zoom.pack(side=tk.RIGHT)

        # ── Controles Novos ──
        ctrl_frame = tk.Frame(win, bg=TEMA['bg_main'])
        ctrl_frame.pack(fill=tk.X, padx=12, pady=(8,0))

        def set_ar(val):
            salvar_estado()
            state['aspect_ratio'] = val
            atualizar_preview()

        def on_tpl_change(e):
            salvar_estado()
            state['template'] = var_tpl.get()
            atualizar_preview()

        def on_gap_change(val):
            state['gap'] = int(float(val))
            atualizar_preview()
            
        def on_rad_change(val):
            state['radius'] = int(float(val))
            atualizar_preview()

        def choose_color():
            c = colorchooser.askcolor(title="Cor de Fundo", initialcolor=state.get('bg_color', '#FFFFFF'))
            if c[1]:
                salvar_estado()
                state['bg_color'] = c[1]
                cfg_c = carregar_config()
                cfg_c['bg_color'] = c[1]
                salvar_config(cfg_c)
                atualizar_preview()

        def choose_bg_image():
            f = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp")])
            if f:
                salvar_estado()
                state['bg_image'] = f
                atualizar_preview()

        def remove_bg_image():
            salvar_estado()
            state['bg_image'] = None
            atualizar_preview()

        # ── Grupos de Controles para o Flow Layout ──
        groups = []
        
        # G1: Proporção
        g_ar = tk.Frame(ctrl_frame, bg=TEMA['bg_main'])
        tk.Label(g_ar, text="Proporção:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(side=tk.LEFT, padx=(0, 5))
        for lab, val in [("Livre", None), ("1:1", 1.0), ("9:16", 9/16), ("4:5", 4/5)]:
            ttk.Button(g_ar, text=lab, command=lambda v=val: set_ar(v), width=6).pack(side=tk.LEFT, padx=1)
        groups.append(g_ar)

        # G2: Template
        g_tpl = tk.Frame(ctrl_frame, bg=TEMA['bg_main'])
        tk.Label(g_tpl, text="Template:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(side=tk.LEFT, padx=(5, 5))
        var_tpl = tk.StringVar(value=state.get('template', 'grade'))
        cb_tpl = ttk.Combobox(g_tpl, textvariable=var_tpl, 
                              values=['grade', 'hero_left', 'hero_right', 'hero_top', 'hero_bottom', 'coluna', 'linha'], 
                              state='readonly', width=12)
        cb_tpl.pack(side=tk.LEFT)
        cb_tpl.bind('<<ComboboxSelected>>', on_tpl_change)
        groups.append(g_tpl)

        # G3: Espaço e Borda
        g_scales = tk.Frame(ctrl_frame, bg=TEMA['bg_main'])
        tk.Label(g_scales, text="Espaço:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(side=tk.LEFT, padx=(5, 2))
        scale_gap = tk.Scale(g_scales, from_=0, to=300, orient=tk.HORIZONTAL, length=60,
                             bg=TEMA['bg_main'], fg=TEMA['text_main'], highlightthickness=0,
                             showvalue=False, command=on_gap_change)
        scale_gap.set(state.get('gap', 0))
        scale_gap.pack(side=tk.LEFT)
        scale_gap.bind('<ButtonPress-1>', lambda e: salvar_estado())
        
        tk.Label(g_scales, text="Borda:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(side=tk.LEFT, padx=(5, 2))
        scale_rad = tk.Scale(g_scales, from_=0, to=300, orient=tk.HORIZONTAL, length=60,
                             bg=TEMA['bg_main'], fg=TEMA['text_main'], highlightthickness=0,
                             showvalue=False, command=on_rad_change)
        scale_rad.set(state.get('radius', 0))
        scale_rad.pack(side=tk.LEFT)
        scale_rad.bind('<ButtonPress-1>', lambda e: salvar_estado())
        groups.append(g_scales)

        # G4: Cores e Fundo
        g_bg = tk.Frame(ctrl_frame, bg=TEMA['bg_main'])
        ttk.Button(g_bg, text="🎨 Cor", command=choose_color, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Button(g_bg, text="🖼️ Foto", command=choose_bg_image, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Button(g_bg, text="❌", command=remove_bg_image, width=3).pack(side=tk.LEFT, padx=1)
        groups.append(g_bg)

        # G5: Recolocar
        g_swap = tk.Frame(ctrl_frame, bg=TEMA['bg_main'])
        tk.Checkbutton(g_swap, text="Recolocar", variable=var_recolocar,
                       bg=TEMA['bg_main'], fg=TEMA['accent'], selectcolor=TEMA['bg_panel'],
                       activebackground=TEMA['bg_main'], activeforeground=TEMA['accent'],
                       font=TEMA['font_title']).pack(side=tk.LEFT, padx=5)
        groups.append(g_swap)

        def flow_layout(event=None):
            # Limpa o pack atual dos grupos
            for g in groups: g.pack_forget()
            
            # Largura disponível
            avail_w = ctrl_frame.winfo_width() - 20
            if avail_w < 100: return
            
            current_w = 0
            for g in groups:
                g.update_idletasks()
                gw = g.winfo_reqwidth()
                if current_w + gw > avail_w:
                    # Quebra linha (aqui simulado pelo pack normal que vai empilhando se não couber no horizontal)
                    # No Tkinter pack, o melhor é usar uma estrutura de linhas ou simplesmente pack top-down
                    # mas para ser fluido vamos usar um truque de side=LEFT e deixar o Win gerenciar?
                    # Na verdade o pack(side=LEFT) não faz wrap sozinho.
                    pass
                
            # Estratégia de wrap real:
            x, y = 0, 0
            row_h = 0
            for g in groups:
                gw = g.winfo_reqwidth()
                gh = g.winfo_reqheight()
                if x + gw > avail_w and x > 0:
                    x = 0
                    y += row_h + 5
                    row_h = 0
                g.place(x=x, y=y)
                x += gw + 15
                row_h = max(row_h, gh)
            
            # Ajusta altura do frame pai
            ctrl_frame.config(height=y + row_h + 5)

        ctrl_frame.bind('<Configure>', flow_layout)
        ctrl_frame.pack_propagate(False)
        ctrl_frame.config(height=40) # altura inicial

        # ── Botões ──

        fb = tk.Frame(win, bg=TEMA['bg_main'])
        fb.pack(pady=8)

        def salvar(fechar=True):
            cfg = carregar_config()
            folder = cfg.get('output_folder') or session['last_folder']
            base = f'colagem_{lote_idx+1}'
            fmt = cfg.get('output_format', '.jpg')
            
            out = session['icones_paths'].get(lote_idx)
            if not out or not out.endswith(fmt):
                out = gerar_nome_unico(folder, base=base, ext=fmt)
                
            make_collage(img_paths, out, state, state.get('gap', 0))
            set_status(f'✅ Colagem {lote_idx+1} salva!\n{out}')
            
            session['lote_states'][lote_idx] = copy.deepcopy(state)
            session['lote_states'][lote_idx]['img_paths'] = img_paths.copy()
            session['icones_paths'][lote_idx] = out
            
            if fechar:
                win.destroy()
            adicionar_icone_colagem(out, img_paths, lote_idx)

        def resetar():
            for i in range(qtd):
                state['offsets'][i] = (0.0, 0.0)
                state['zooms'][i]   = 1.0
            state['col_frac'] = [1.0/cols]*cols
            state['row_frac'] = [1.0/rows]*rows
            state['gap'] = 0
            lbl_zoom.config(text='')
            redesenhar()

        ttk.Button(fb, text='💾 Salvar Colagem',  command=salvar).pack(side=tk.LEFT, padx=6)
        ttk.Button(fb, text='↺ Resetar ajustes', command=resetar).pack(side=tk.LEFT, padx=6)
        ttk.Button(fb, text='✖ Fechar',           command=win.destroy).pack(side=tk.LEFT, padx=6)

    # ── Ícone de colagem salva na barra superior ────────────────

    def adicionar_icone_colagem(output_path, image_paths, lote_idx):
        """Cria ou atualiza o thumbnail clicável na barra de ícones."""
        ICON_SIZE = 54
        img = Image.open(output_path)
        img.thumbnail((ICON_SIZE, ICON_SIZE), Image.LANCZOS)

        bordered = Image.new('RGB', (ICON_SIZE + 4, ICON_SIZE + 4), TEMA['accent'])
        bordered.paste(img, (2, 2))
        tk_img = ImageTk.PhotoImage(bordered)
        session['icones_refs'].append(tk_img)   # anti garbage-collect
        session['icones_paths'][lote_idx] = output_path

        num = lote_idx + 1

        # ── Atualiza ícone existente (re-save) ──────────────────
        if lote_idx in session['icones_widgets']:
            w = session['icones_widgets'][lote_idx]
            w['btn'].config(image=tk_img)
            w['btn']._img = tk_img   # referência extra por segurança

            # Atualiza binding para usar a nova lista de caminhos
            def abrir_edicao_novo(event=None, _paths=list(image_paths), _idx=lote_idx):
                abrir_preview(_paths, _idx)
            w['btn'].bind('<Button-1>', abrir_edicao_novo)
            w['lbl'].bind('<Button-1>', abrir_edicao_novo)
            return

        # ── Cria novo ícone ─────────────────────────────────────
        frame_ico = tk.Frame(icones_frame, bg=TEMA['bg_main'], cursor='hand2')
        frame_ico.pack(side=tk.LEFT, padx=4, pady=2)

        btn = tk.Label(frame_ico, image=tk_img, bg=TEMA['bg_main'],
                       cursor='hand2', relief='flat')
        btn._img = tk_img
        btn.pack()

        lbl = tk.Label(frame_ico, text=f'C{num}',
                       fg=TEMA['text_main'], bg=TEMA['bg_main'], font=('Segoe UI', 8, 'bold'))
        lbl.pack()

        session['icones_widgets'][lote_idx] = {'frame': frame_ico, 'btn': btn, 'lbl': lbl}

        def abrir_edicao(event=None, _paths=list(image_paths), _idx=lote_idx):
            abrir_preview(_paths, _idx)

        btn.bind('<Button-1>', abrir_edicao)
        lbl.bind('<Button-1>', abrir_edicao)

        # tooltip com nome do arquivo
        _tip = [None]
        def on_enter(e):
            lbl.config(fg=TEMA['accent_hi'])
            if _tip[0]:
                _tip[0].destroy()
            tip = tk.Toplevel(parent)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f'+{e.x_root+12}+{e.y_root+12}')
            tk.Label(tip, text=os.path.basename(output_path),
                     bg=TEMA['bg_panel'], fg=TEMA['text_main'],
                     font=TEMA['font_small'], padx=6, pady=3,
                     relief='solid', borderwidth=1, highlightbackground=TEMA['accent']).pack()
            _tip[0] = tip
        def on_leave(e):
            lbl.config(fg=TEMA['text_main'])
            if _tip[0]:
                _tip[0].destroy()
                _tip[0] = None
        btn.bind('<Enter>', on_enter);  btn.bind('<Leave>', on_leave)
        lbl.bind('<Enter>', on_enter);  lbl.bind('<Leave>', on_leave)

    def limpar_icones():
        """Remove todos os ícones da barra e limpa o registro."""
        for w in session['icones_widgets'].values():
            w['frame'].destroy()
        session['icones_widgets'].clear()
        session['icones_paths'].clear()
        session['icones_refs'].clear()
        session['lote_states'].clear()

    # ── Processar drop na área principal ───────────────────────

    def gerar_colagem_automatica(image_paths_in, lote_idx):
        img_paths = list(image_paths_in)
        qtd = len(img_paths)
        rows, cols = escolher_layout(qtd)
        
        cfg = carregar_config()
        auto_cfg = session.get('auto_settings', {})
        
        state = {
            'offsets':  {i: (0.0, 0.0) for i in range(qtd)},
            'col_frac': [1.0/cols] * cols,
            'row_frac': [1.0/rows] * rows,
            'gap':      auto_cfg.get('gap', 0),
            'zooms':    {i: 1.0 for i in range(qtd)},
            'bg_color': auto_cfg.get('bg_color', '#FFFFFF'),
            'aspect_ratio': auto_cfg.get('aspect_ratio'),
            'transforms': {i: {'rotate': 0, 'flip_h': False, 'flip_v': False} for i in range(qtd)},
            'filters': {i: {'type': 'normal', 'brightness': 1.0} for i in range(qtd)},
            'radius': auto_cfg.get('radius', 0),
            'template': auto_cfg.get('template', 'grade'),
            'bg_image': auto_cfg.get('bg_image')
        }
        
        folder = cfg.get('output_folder') or session['last_folder']
        base = f'colagem_{lote_idx+1}'
        fmt = cfg.get('output_format', '.jpg')
        
        out = session['icones_paths'].get(lote_idx)
        if not out or not out.endswith(fmt):
            out = gerar_nome_unico(folder, base=base, ext=fmt)
        
        try:
            make_collage(img_paths, out, state, state.get('gap', 0))
            
            session['lote_states'][lote_idx] = copy.deepcopy(state)
            session['lote_states'][lote_idx]['img_paths'] = img_paths.copy()
            session['icones_paths'][lote_idx] = out
            
            parent.after(0, adicionar_icone_colagem, out, img_paths.copy(), lote_idx)
        except Exception as e:
            parent.after(0, set_status, f'Erro na colagem automática {lote_idx+1}: {e}')

    def process_images(image_files):
        image_files = [f for f in image_files
                       if os.path.isfile(f) and f.lower().endswith(
                           ('.jpg','.jpeg','.png','.bmp','.webp'))]
        if not image_files:
            set_status('Nenhuma imagem válida encontrada.')
            return
        
        # Calcular offset inicial para não sobrepor ícones anteriores
        start_idx = 0
        if session['icones_widgets']:
            start_idx = max(session['icones_widgets'].keys()) + 1
            
        session['images'] = image_files
        session['last_folder'] = os.path.dirname(os.path.abspath(image_files[0]))
        bs    = session['batch_size']
        lotes = [image_files[i:i+bs] for i in range(0, len(image_files), bs)]
        set_status(f'✅ {len(image_files)} imagem(ns)  →  {len(lotes)} colagem(ns) geradas.')
        btn_excluir.config(state=tk.NORMAL)
        
        if session.get('auto_colagem', False):
            progress_bar.pack(side=tk.RIGHT, padx=12, fill=tk.X, expand=True)
            progress_var.set(0)
            
            def worker():
                for idx, lote in enumerate(lotes):
                    real_idx = start_idx + idx
                    gerar_colagem_automatica(lote, real_idx)
                    pct = (idx + 1) / len(lotes) * 100
                    parent.after(0, progress_var.set, pct)
                parent.after(500, progress_bar.pack_forget)

            threading.Thread(target=worker, daemon=True).start()
        else:
            for idx, lote in enumerate(lotes):
                abrir_preview(lote, start_idx + idx)

    def drop(event):
        process_images(list(parent.tk.splitlist(event.data)))

    def excluir_imagens():
        """Move para a lixeira do sistema operacional."""
        falhas = []
        for p in session['images']:
            if not os.path.exists(p):
                continue
            try:
                mover_para_lixeira(p)
            except Exception as e:
                falhas.append(f'{os.path.basename(p)}: {e}')
        if falhas:
            set_status('Erro ao mover para lixeira:\n' + '\n'.join(falhas))
        else:
            set_status('✅ Imagens movidas para a lixeira do sistema!')
        session['images'] = []
        btn_excluir.config(state=tk.DISABLED)

    # ── Interface principal ─────────────────────────────────────

    top_bar = tk.Frame(parent, bg=TEMA['bg_panel'], pady=10)
    top_bar.pack(fill=tk.X)

    tk.Label(top_bar, text='Fotos por colagem:',
             fg=TEMA['text_main'], bg=TEMA['bg_panel'], font=TEMA['font_title']).pack(side=tk.LEFT, padx=(20,10))

    var_batch = tk.IntVar(value=session['batch_size'])
    
    def on_batch_change(*args):
        try:
            val = var_batch.get()
            if val < 1: val = 1
            if val > 50: val = 50
            session['batch_size'] = val
        except:
            pass

    var_batch.trace_add('write', on_batch_change)

    spin_batch = ttk.Spinbox(top_bar, from_=1, to=50, textvariable=var_batch, width=5, font=('Segoe UI', 12, 'bold'))
    spin_batch.pack(side=tk.LEFT, padx=8)

    tk.Label(top_bar, text='foto(s)',
             fg=TEMA['text_sec'], bg=TEMA['bg_panel'], font=TEMA['font_small']).pack(side=tk.LEFT)

    def abrir_configuracoes_auto():
        auto_cfg = session['auto_settings']
        # Cópia temporária para o preview não afetar o config até salvar
        preview_state = copy.deepcopy(auto_cfg)
        
        awin = tk.Toplevel(parent)
        awin.title("Configurações Automáticas com Preview")
        awin.geometry("920x520")
        awin.configure(bg=TEMA['bg_main'])
        awin.transient(parent)
        awin.grab_set()

        main_split = tk.Frame(awin, bg=TEMA['bg_main'])
        main_split.pack(fill=tk.BOTH, expand=True)

        f_left = tk.Frame(main_split, bg=TEMA['bg_main'], padx=20, pady=20, width=380)
        f_left.pack(side=tk.LEFT, fill=tk.BOTH)
        f_left.pack_propagate(False)

        f_right = tk.Frame(main_split, bg=TEMA['bg_panel'], padx=10, pady=10)
        f_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Área de Preview (Direita) ──
        tk.Label(f_right, text="Pré-visualização (Exemplo com 4 fotos)", 
                 bg=TEMA['bg_panel'], fg=TEMA['text_sec'], font=TEMA['font_small']).pack(pady=(0,10))
        
        preview_canvas = tk.Canvas(f_right, bg=TEMA['bg_main'], highlightthickness=1, highlightbackground=TEMA['accent'])
        preview_canvas.pack(expand=True)

        def redesenhar_auto_preview(event=None):
            preview_canvas.delete("all")
            aw = f_right.winfo_width() - 40
            ah = f_right.winfo_height() - 80
            if aw < 50 or ah < 50: return

            # Simular 4 fotos
            qtd = 4
            rows, cols = escolher_layout(qtd)
            
            # Cálculo de escala para o preview
            base_w, base_h = 400, 300
            ar = preview_state.get('aspect_ratio')
            if ar:
                if base_w / base_h > ar: base_h = int(base_w / ar)
                else: base_w = int(base_h * ar)
            
            sc = min(aw / (base_w + 20), ah / (base_h + 20), 1.0)
            pw, ph = int(base_w * sc), int(base_h * sc)
            
            preview_canvas.config(width=pw, height=ph)
            
            # Fundo
            bg_c = preview_state.get('bg_color', '#FFFFFF')
            preview_canvas.create_rectangle(0, 0, pw, ph, fill=bg_c, outline='')
            
            # Gap e Radius escalados de forma mais sutil
            gap_vis = int(preview_state.get('gap', 0) * sc * 0.15) 
            rad_vis = int(preview_state.get('radius', 0) * sc * 0.15)
            
            state_mock = {
                'template': preview_state.get('template', 'grade'),
                'col_frac': [1.0/cols]*cols,
                'row_frac': [1.0/rows]*rows,
                'gap': preview_state.get('gap', 0)
            }
            rects = calc_cell_rects(pw, ph, qtd, cols, state_mock, gap_vis)
            
            colors = ["#6366F1", "#10B981", "#F59E0B", "#EF4444"]
            for i, (rx, ry, rw, rh) in enumerate(rects):
                if i >= len(colors): break
                c = colors[i]
                
                if rad_vis > 2:
                    r = min(rad_vis, rw/2, rh/2)
                    # Cantos
                    preview_canvas.create_arc(rx, ry, rx+2*r, ry+2*r, start=90, extent=90, fill=c, outline='')
                    preview_canvas.create_arc(rx+rw-2*r, ry, rx+rw, ry+2*r, start=0, extent=90, fill=c, outline='')
                    preview_canvas.create_arc(rx, ry+rh-2*r, rx+2*r, ry+rh, start=180, extent=90, fill=c, outline='')
                    preview_canvas.create_arc(rx+rw-2*r, ry+rh-2*r, rx+rw, ry+rh, start=270, extent=90, fill=c, outline='')
                    # Corpos
                    preview_canvas.create_rectangle(rx+r, ry, rx+rw-r, ry+rh, fill=c, outline='')
                    preview_canvas.create_rectangle(rx, ry+r, rx+rw, ry+rh-r, fill=c, outline='')
                else:
                    preview_canvas.create_rectangle(rx, ry, rx+rw, ry+rh, fill=c, outline='')
                
                preview_canvas.create_text(rx+rw/2, ry+rh/2, text=f"Foto {i+1}", fill="white", font=('Segoe UI', 8, 'bold'))

        f_right.bind("<Configure>", lambda e: awin.after(10, redesenhar_auto_preview))

        # ── Controles (Esquerda) ──
        tk.Label(f_left, text="Proporção da Colagem:", bg=TEMA['bg_main'], fg=TEMA['text_main'], font=TEMA['font_title']).pack(anchor='w', pady=(0,5))
        ar_frame = tk.Frame(f_left, bg=TEMA['bg_main'])
        ar_frame.pack(fill=tk.X, pady=(0,15))
        
        var_ar = tk.StringVar(value="Livre")
        
        def update_ar_var():
            curr = preview_state.get('aspect_ratio')
            if curr == 1.0: var_ar.set("1:1")
            elif curr == 9/16: var_ar.set("9:16")
            elif curr == 4/5: var_ar.set("4:5")
            else: var_ar.set("Livre")
        
        update_ar_var()
        
        def set_ar_auto(lab, val):
            preview_state['aspect_ratio'] = val
            var_ar.set(lab)
            redesenhar_auto_preview()
            
        for lab, val in [("Livre", None), ("1:1", 1.0), ("9:16", 9/16), ("4:5", 4/5)]:
            tk.Radiobutton(ar_frame, text=lab, variable=var_ar, value=lab, 
                           command=lambda l=lab, v=val: set_ar_auto(l, v),
                           bg=TEMA['bg_main'], fg=TEMA['text_main'], selectcolor=TEMA['bg_panel'],
                           activebackground=TEMA['bg_main'], activeforeground=TEMA['accent'],
                           font=TEMA['font_small']).pack(side=tk.LEFT, padx=2)

        # Template
        tk.Label(f_left, text="Template padrão:", bg=TEMA['bg_main'], fg=TEMA['text_main'], font=TEMA['font_title']).pack(anchor='w', pady=(0,5))
        var_tpl_auto = tk.StringVar(value=preview_state.get('template', 'grade'))
        
        def on_tpl_auto_change(e):
            preview_state['template'] = var_tpl_auto.get()
            redesenhar_auto_preview()

        cb_tpl_auto = ttk.Combobox(f_left, textvariable=var_tpl_auto, 
                                   values=['grade', 'hero_left', 'hero_right', 'hero_top', 'hero_bottom', 'coluna', 'linha'], 
                                   state='readonly')
        cb_tpl_auto.pack(fill=tk.X, pady=(0,15))
        cb_tpl_auto.bind('<<ComboboxSelected>>', on_tpl_auto_change)

        # Sliders: Espaço e Borda
        tk.Label(f_left, text="Espaço entre fotos:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(anchor='w')
        var_gap = tk.IntVar(value=preview_state.get('gap', 0))
        def on_gap_auto_move(v):
            preview_state['gap'] = int(float(v))
            redesenhar_auto_preview()
        tk.Scale(f_left, from_=0, to=200, orient=tk.HORIZONTAL, variable=var_gap,
                 bg=TEMA['bg_main'], fg=TEMA['text_main'], highlightthickness=0, command=on_gap_auto_move).pack(fill=tk.X, pady=(0,10))

        tk.Label(f_left, text="Arredondamento cantos:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(anchor='w')
        var_rad = tk.IntVar(value=preview_state.get('radius', 0))
        def on_rad_auto_move(v):
            preview_state['radius'] = int(float(v))
            redesenhar_auto_preview()
        tk.Scale(f_left, from_=0, to=200, orient=tk.HORIZONTAL, variable=var_rad,
                 bg=TEMA['bg_main'], fg=TEMA['text_main'], highlightthickness=0, command=on_rad_auto_move).pack(fill=tk.X, pady=(0,15))

        # Fundo
        tk.Label(f_left, text="Fundo da Colagem:", bg=TEMA['bg_main'], fg=TEMA['text_main'], font=TEMA['font_title']).pack(anchor='w', pady=(0,5))
        bg_btn_frame = tk.Frame(f_left, bg=TEMA['bg_main'])
        bg_btn_frame.pack(fill=tk.X, pady=(0,10))
        
        def pick_color_auto():
            c = colorchooser.askcolor(title="Cor de Fundo", initialcolor=preview_state.get('bg_color', '#FFFFFF'))
            if c[1]: 
                preview_state['bg_color'] = c[1]
                redesenhar_auto_preview()

        def pick_bg_img_auto():
            fl = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp")])
            if fl: 
                preview_state['bg_image'] = fl
                redesenhar_auto_preview()

        ttk.Button(bg_btn_frame, text="🎨 Cor", command=pick_color_auto).pack(side=tk.LEFT, padx=(0,5), expand=True, fill=tk.X)
        ttk.Button(bg_btn_frame, text="🖼️ Foto", command=pick_bg_img_auto).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(bg_btn_frame, text="❌", command=lambda: [preview_state.update(bg_image=None), redesenhar_auto_preview()], width=5).pack(side=tk.LEFT)

        def resetar_auto():
            default = {
                'gap': 0, 'radius': 0, 'bg_color': '#FFFFFF',
                'aspect_ratio': None, 'template': 'grade', 'bg_image': None
            }
            preview_state.clear()
            preview_state.update(default)
            var_gap.set(0)
            var_rad.set(0)
            var_tpl_auto.set("grade")
            update_ar_var()
            redesenhar_auto_preview()

        def salvar_auto_settings():
            # Atualiza o dicionário da sessão e do config.json
            session['auto_settings'].clear()
            session['auto_settings'].update(preview_state)
            
            cfg_s = carregar_config()
            cfg_s['auto_settings'] = session['auto_settings']
            salvar_config(cfg_s)
            
            set_status("✅ Configurações automáticas salvas!")
            awin.destroy()

        btn_f = tk.Frame(f_left, bg=TEMA['bg_main'])
        btn_f.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        ttk.Button(btn_f, text="↺ Resetar", command=resetar_auto).pack(side=tk.LEFT, padx=(0,5), expand=True, fill=tk.X)
        ttk.Button(btn_f, text="💾 Salvar", command=salvar_auto_settings).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Initial draw
        awin.after(150, redesenhar_auto_preview)

    def abrir_configuracoes():
        cfg = carregar_config()
        
        cwin = tk.Toplevel(parent)
        cwin.title("Configurações")
        cwin.geometry("400x350")
        cwin.configure(bg=TEMA['bg_main'])
        cwin.transient(parent)
        cwin.grab_set()

        f = tk.Frame(cwin, bg=TEMA['bg_main'], padx=20, pady=20)
        f.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(f, text="Formato de Saída:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(anchor='w')
        var_fmt = tk.StringVar(value=cfg.get('output_format', '.jpg'))
        cb_fmt = ttk.Combobox(f, textvariable=var_fmt, values=['.jpg', '.png', '.webp'], state='readonly')
        cb_fmt.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(f, text="Qualidade JPG/WEBP (10-100):", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(anchor='w')
        var_qual = tk.IntVar(value=cfg.get('jpeg_quality', 95))
        scale_qual = tk.Scale(f, from_=10, to=100, orient=tk.HORIZONTAL, variable=var_qual,
                              bg=TEMA['bg_main'], fg=TEMA['text_main'], highlightthickness=0)
        scale_qual.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(f, text="Pasta de Saída Padrão:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(anchor='w')
        var_folder = tk.StringVar(value=cfg.get('output_folder', ''))
        
        def pick_folder():
            d = filedialog.askdirectory(initialdir=var_folder.get() or None)
            if d: var_folder.set(d)
            
        f_folder = tk.Frame(f, bg=TEMA['bg_main'])
        f_folder.pack(fill=tk.X, pady=(0, 15))
        tk.Entry(f_folder, textvariable=var_folder, bg=TEMA['bg_panel'], fg=TEMA['text_main'], insertbackground=TEMA['text_main']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(f_folder, text="...", command=pick_folder, width=3).pack(side=tk.LEFT)
        
        tk.Label(f, text="*Deixe em branco para salvar na pasta original das fotos", fg=TEMA['text_sec'], bg=TEMA['bg_main'], font=TEMA['font_small']).pack(anchor='w', pady=(0, 15))

        tk.Label(f, text="Marca D'água:", bg=TEMA['bg_main'], fg=TEMA['text_main']).pack(anchor='w')
        var_wm = tk.StringVar(value=cfg.get('watermark', ''))
        tk.Entry(f, textvariable=var_wm, bg=TEMA['bg_panel'], fg=TEMA['text_main'], insertbackground=TEMA['text_main']).pack(fill=tk.X, pady=(0, 15))

        def salvar_configs():
            cfg['output_format'] = var_fmt.get()
            cfg['jpeg_quality'] = var_qual.get()
            cfg['output_folder'] = var_folder.get()
            cfg['watermark'] = var_wm.get()
            salvar_config(cfg)
            cwin.destroy()
            
        ttk.Button(f, text="Salvar", command=salvar_configs).pack(pady=10)

    btn_cfg = ttk.Button(top_bar, text='⚙️', command=abrir_configuracoes, width=3)
    btn_cfg.pack(side=tk.RIGHT, padx=12)

    def alternar_tema():
        cfg_tema = carregar_config()
        cfg_tema['is_dark'] = not is_dark
        salvar_config(cfg_tema)
        montar_colagem_interface(parent, session)

    btn_tema = ttk.Button(top_bar, text='☀️ Modo Claro' if is_dark else '🌙 Modo Escuro',
                          command=alternar_tema)
    btn_tema.pack(side=tk.RIGHT, padx=12)

    # ── Barra de ícones das colagens salvas ──────────────────────
    icones_outer = tk.Frame(parent, bg=TEMA['bg_main'], pady=8)
    icones_outer.pack(fill=tk.X, padx=12)

    icones_canvas = tk.Canvas(icones_outer, bg=TEMA['bg_main'], highlightthickness=0, height=85)
    icones_scroll = ttk.Scrollbar(icones_outer, orient=tk.HORIZONTAL, command=icones_canvas.xview)
    icones_canvas.configure(xscrollcommand=icones_scroll.set)

    icones_scroll.pack(side=tk.BOTTOM, fill=tk.X)
    icones_canvas.pack(side=tk.TOP, fill=tk.X, expand=True)

    icones_frame = tk.Frame(icones_canvas, bg=TEMA['bg_main'])
    icones_canvas.create_window((0, 0), window=icones_frame, anchor='nw')

    def on_icones_configure(event):
        icones_canvas.configure(scrollregion=icones_canvas.bbox("all"))

    icones_frame.bind("<Configure>", on_icones_configure)

    def _on_mousewheel(event):
        # No Windows, event.delta é múltiplo de 120
        icones_canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    def _bound_to_mousewheel(event):
        icones_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _unbound_to_mousewheel(event):
        icones_canvas.unbind_all("<MouseWheel>")

    icones_outer.bind('<Enter>', _bound_to_mousewheel)
    icones_outer.bind('<Leave>', _unbound_to_mousewheel)

    # Label de drop customizado, sem bg claro, usando Canvas para melhor efeito ou um Frame elegante
    drop_frame = tk.Frame(parent, bg=TEMA['bg_main'], padx=20, pady=20)
    drop_frame.pack(expand=True, fill=tk.BOTH)

    drop_inner = tk.Frame(drop_frame, bg=TEMA['bg_drop'], bd=0)
    drop_inner.pack(expand=True, fill=tk.BOTH)

    # Falso borda tracejada / visual
    drop_canvas = tk.Canvas(drop_inner, bg=TEMA['bg_drop'], highlightthickness=0)
    drop_canvas.pack(expand=True, fill=tk.BOTH)

    def draw_dashed_border(event=None):
        drop_canvas.delete("border")
        w = drop_canvas.winfo_width()
        h = drop_canvas.winfo_height()
        if w > 10 and h > 10:
            drop_canvas.create_rectangle(10, 10, w-10, h-10, outline=TEMA['accent'], width=2, dash=(8, 8), tags="border")
    
    drop_canvas.bind("<Configure>", draw_dashed_border)

    lbl_drop_text = tk.Label(drop_inner, text='✦ Arraste as imagens aqui ✦',
                             font=('Segoe UI', 20, 'bold'), fg=TEMA['text_sec'], bg=TEMA['bg_drop'])
    lbl_drop_text.place(relx=0.5, rely=0.5, anchor='center')

    # Registra eventos de drop no canvas e label interior
    drop_canvas.drop_target_register(DND_FILES)
    drop_canvas.dnd_bind('<<Drop>>', drop)
    lbl_drop_text.drop_target_register(DND_FILES)
    lbl_drop_text.dnd_bind('<<Drop>>', drop)
    drop_inner.drop_target_register(DND_FILES)
    drop_inner.dnd_bind('<<Drop>>', drop)

    def on_drop_enter(e):
        lbl_drop_text.config(fg=TEMA['text_main'])
    def on_drop_leave(e):
        lbl_drop_text.config(fg=TEMA['text_sec'])

    drop_canvas.bind('<Enter>', on_drop_enter)
    drop_canvas.bind('<Leave>', on_drop_leave)

    bot_bar = tk.Frame(parent, bg=TEMA['bg_panel'], pady=10)
    bot_bar.pack(fill=tk.X, side=tk.BOTTOM)

    btn_excluir = ttk.Button(bot_bar, text='🗑 Mover Imagens para Lixeira',
                              state=tk.NORMAL if session['images'] else tk.DISABLED, command=excluir_imagens)
    btn_excluir.pack(side=tk.LEFT, padx=12)

    ttk.Button(bot_bar, text='✖ Limpar Ícones',
               command=limpar_icones).pack(side=tk.LEFT, padx=4)

    var_auto = tk.BooleanVar(value=session.get('auto_colagem', False))
    btn_auto_cfg = ttk.Button(bot_bar, text='⚙️', command=abrir_configuracoes_auto, width=3)

    def on_auto_change():
        is_auto = var_auto.get()
        session['auto_colagem'] = is_auto
        cfg_auto = carregar_config()
        cfg_auto['auto_colagem'] = is_auto
        salvar_config(cfg_auto)
        
        if is_auto:
            btn_auto_cfg.pack(side=tk.LEFT, padx=(0, 12))
        else:
            btn_auto_cfg.pack_forget()

    chk_auto = tk.Checkbutton(bot_bar, text="Colagem Automática", variable=var_auto, command=on_auto_change,
                              bg=TEMA['bg_panel'], fg=TEMA['text_main'], selectcolor=TEMA['bg_main'],
                              activebackground=TEMA['bg_panel'], activeforeground=TEMA['accent_hi'])
    chk_auto.pack(side=tk.LEFT, padx=12)

    if var_auto.get():
        btn_auto_cfg.pack(side=tk.LEFT, padx=(0, 12))

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(bot_bar, variable=progress_var, maximum=100)
    
    status_var = tk.StringVar(value=session['status_msg'])
    status_lbl = tk.Label(parent, textvariable=status_var,
                          fg='#10B981', bg=TEMA['bg_main'], font=TEMA['font_small'],
                          wraplength=900, justify='left')
    status_lbl.pack(pady=6, side=tk.BOTTOM, fill=tk.X)

    # Reconstruir ícones existentes se a sessão já tinha
    for lote_idx, out_path in list(session['icones_paths'].items()):
        if lote_idx in session['lote_states']:
            state = session['lote_states'][lote_idx]
            # Migração de estados antigos / failsafe
            qtd = len(state.get('img_paths', []))
            if 'transforms' not in state:
                state['transforms'] = {i: {'rotate': 0, 'flip_h': False, 'flip_v': False} for i in range(qtd)}
            if 'filters' not in state:
                state['filters'] = {i: {'type': 'normal', 'brightness': 1.0} for i in range(qtd)}
            if 'radius' not in state: state['radius'] = 0
            if 'template' not in state: state['template'] = 'grade'
            
            img_paths = state['img_paths']
            adicionar_icone_colagem(out_path, img_paths, lote_idx)


# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    import sys

    from tkinterdnd2 import TkinterDnD
    root = TkinterDnD.Tk()
    root.title('Colagem Inteligente')
    
    # Removemos o carregamento da geometria anterior para garantir 
    # que o app abra no menor tamanho possível que comporte o conteúdo.
    root.minsize(550, 400)

    frame = tk.Frame(root)
    frame.pack(expand=True, fill='both')
    montar_colagem_interface(frame)
    root.mainloop()
