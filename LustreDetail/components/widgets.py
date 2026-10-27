"""Fábricas de widgets com o estilo do Lustre Detail (campos, botões, rótulos, cartões).

Usar estas funções em vez de instanciar ``CTk*`` diretamente garante que todos
os componentes respeitem a mesma identidade visual.
"""
from typing import Callable, Optional

import customtkinter as ctk

from utils import colors as C
from utils.animation import Debouncer
from utils.fonts import display_font, text_font
from utils.icons import get_icon
from utils.theme import RADIUS, RADIUS_SM


# ------------------------------------------------------------------- rótulos
def label(parent, text="", size=13, color=C.TEXT, weight="normal", display=False,
          anchor="w", height=None, **kw) -> ctk.CTkLabel:
    """Rótulo de texto. ``display=True`` usa a fonte de títulos (Barlow Condensed)."""
    font = display_font(size, weight) if display else text_font(size, weight)
    if height is None:
        height = int(size * 1.7)
    return ctk.CTkLabel(parent, text=text, font=font, text_color=color,
                        anchor=anchor, height=height, **kw)


def caption(parent, text: str) -> ctk.CTkLabel:
    """Texto pequeno em caixa-alta para títulos de campo/seção."""
    return label(parent, text.upper(), 11, C.TEXT_SECONDARY, "bold", height=18)


# ------------------------------------------------------------------- botões
_BUTTON_STYLES = {
    "primary": dict(fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER, text_color=C.BG,
                    border_width=0, icon_color=C.BG),
    "ghost": dict(fg_color="transparent", hover_color=C.SURFACE_HOVER, text_color=C.TEXT,
                  border_width=1, border_color=C.BORDER, icon_color=C.TEXT_SECONDARY),
    "danger": dict(fg_color="transparent", hover_color=C.tint(C.DANGER, 0.14),
                   text_color=C.DANGER, border_width=1,
                   border_color=C.tint(C.DANGER, 0.5), icon_color=C.DANGER),
    "link": dict(fg_color="transparent", hover_color=C.SURFACE_HOVER, text_color=C.ACCENT,
                 border_width=0, icon_color=C.ACCENT),
    "icon": dict(fg_color="transparent", hover_color=C.SURFACE_HOVER,
                 text_color=C.TEXT_SECONDARY, border_width=0, icon_color=C.TEXT_SECONDARY),
    "icon_danger": dict(fg_color="transparent", hover_color=C.tint(C.DANGER, 0.16),
                        text_color=C.DANGER, border_width=0, icon_color=C.DANGER),
}


def button(parent, text="", command: Optional[Callable] = None, kind="primary", icon=None,
           width=None, height=34, size=13, **kw) -> ctk.CTkButton:
    """Botão estilizado. ``kind``: primary, ghost, danger, link, icon, icon_danger."""
    style = dict(_BUTTON_STYLES[kind])
    icon_color = style.pop("icon_color")
    if width is None:
        if text:
            width = int(len(text) * size * 0.6 + 32 + (20 if icon else 0))
            width = max(width, 64)
        else:
            width = height
    image = get_icon(icon, 16, icon_color) if icon else None
    weight = "bold" if kind == "primary" else "normal"
    return ctk.CTkButton(parent, text=text, command=command, image=image, compound="left",
                         width=width, height=height, corner_radius=RADIUS_SM,
                         font=text_font(size, weight), **style, **kw)


def icon_button(parent, icon: str, command: Callable, danger=False, size=30) -> ctk.CTkButton:
    """Botão quadrado só com ícone (usado nas linhas das tabelas)."""
    return button(parent, "", command, "icon_danger" if danger else "icon", icon=icon,
                  width=size, height=size)


def action_bar(parent, actions) -> ctk.CTkFrame:
    """Barra de ícones para linhas de tabela.

    ``actions``: lista de tuplas ``(icone, comando, perigo)``; o comando recebe o
    próprio botão (útil para ancorar menus).
    """
    bar = ctk.CTkFrame(parent, fg_color="transparent")
    for i, (icon, command, danger) in enumerate(actions):
        btn = icon_button(bar, icon, lambda: None, danger)
        btn.configure(command=lambda b=btn, c=command: c(b))
        btn.grid(row=0, column=i, padx=(0, 2))
    return bar


# ------------------------------------------------------------------- campos
def entry(parent, placeholder="", width=240, height=34, **kw) -> ctk.CTkEntry:
    """Campo de texto com destaque âmbar ao receber foco."""
    e = ctk.CTkEntry(parent, placeholder_text=placeholder, width=width, height=height,
                     corner_radius=RADIUS_SM, border_width=1, fg_color=C.BG,
                     border_color=C.BORDER, text_color=C.TEXT,
                     placeholder_text_color=C.TEXT_MUTED, font=text_font(13), **kw)
    e.bind("<FocusIn>", lambda ev: e.configure(border_color=C.ACCENT), add="+")
    e.bind("<FocusOut>", lambda ev: e.configure(border_color=C.BORDER), add="+")
    return e


def combo(parent, values, command: Optional[Callable] = None, width=220, height=34) -> ctk.CTkComboBox:
    """Lista de seleção somente leitura (o usuário escolhe, não digita)."""
    values = list(values) or [""]
    cb = ctk.CTkComboBox(parent, values=values, command=command, width=width, height=height,
                         state="readonly", corner_radius=RADIUS_SM, border_width=1,
                         fg_color=C.BG, border_color=C.BORDER, button_color=C.BORDER,
                         button_hover_color=C.TEXT_MUTED, text_color=C.TEXT,
                         dropdown_fg_color=C.SURFACE, dropdown_hover_color=C.SURFACE_HOVER,
                         dropdown_text_color=C.TEXT, font=text_font(13),
                         dropdown_font=text_font(13))
    cb.set(values[0])
    return cb


def textbox(parent, height=80, width=240) -> ctk.CTkTextbox:
    """Caixa de texto de várias linhas."""
    tb = ctk.CTkTextbox(parent, height=height, width=width, corner_radius=RADIUS_SM,
                        border_width=1, border_color=C.BORDER, fg_color=C.BG,
                        text_color=C.TEXT, font=text_font(13), wrap="word")
    tb.bind("<FocusIn>", lambda ev: tb.configure(border_color=C.ACCENT), add="+")
    tb.bind("<FocusOut>", lambda ev: tb.configure(border_color=C.BORDER), add="+")
    return tb


def checkbox(parent, text: str) -> ctk.CTkCheckBox:
    """Caixa de seleção no estilo do sistema."""
    return ctk.CTkCheckBox(parent, text=text, font=text_font(13), text_color=C.TEXT,
                           fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER,
                           border_color=C.TEXT_MUTED, checkmark_color=C.BG,
                           corner_radius=4, border_width=1)


def search_box(parent, placeholder="Buscar…", width=260, on_change: Optional[Callable] = None):
    """Campo de busca com ícone. Devolve ``(frame, entry)``.

    ``on_change(texto)`` é chamado com atraso curto após a digitação (debounce).
    """
    frame = ctk.CTkFrame(parent, fg_color=C.BG, border_width=1, border_color=C.BORDER,
                         corner_radius=RADIUS_SM, width=width, height=34)
    frame.grid_propagate(False)
    frame.grid_columnconfigure(1, weight=1)
    frame.grid_rowconfigure(0, weight=1)
    ctk.CTkLabel(frame, text="", image=get_icon("search", 16, C.TEXT_MUTED), width=28
                 ).grid(row=0, column=0, padx=(8, 0))
    e = ctk.CTkEntry(frame, placeholder_text=placeholder, border_width=0, fg_color="transparent",
                     text_color=C.TEXT, placeholder_text_color=C.TEXT_MUTED, font=text_font(13),
                     height=30)
    e.grid(row=0, column=1, sticky="ew", padx=(0, 6))
    e.bind("<FocusIn>", lambda ev: frame.configure(border_color=C.ACCENT), add="+")
    e.bind("<FocusOut>", lambda ev: frame.configure(border_color=C.BORDER), add="+")
    if on_change:
        deb = Debouncer(frame)
        e.bind("<KeyRelease>", lambda ev: deb.call(lambda: on_change(e.get())), add="+")
    return frame, e


# -------------------------------------------------------------------- caixas
def card(parent, **kw) -> ctk.CTkFrame:
    """Painel discreto: superfície escura com borda fina."""
    opts = dict(fg_color=C.SURFACE, border_width=1, border_color=C.BORDER, corner_radius=RADIUS)
    opts.update(kw)
    return ctk.CTkFrame(parent, **opts)


def bind_hover(widget, on_enter: Callable, on_leave: Callable) -> None:
    """Hover robusto: vale para o widget e todos os filhos (sem 'piscar')."""

    def inside() -> bool:
        try:
            x, y = widget.winfo_pointerxy()
            wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
            return wx <= x < wx + widget.winfo_width() and wy <= y < wy + widget.winfo_height()
        except Exception:
            return False

    def _enter(_e=None):
        on_enter()

    def _leave(_e=None):
        if not inside():
            on_leave()

    def _bind(w):
        try:
            w.bind("<Enter>", _enter, add="+")
            w.bind("<Leave>", _leave, add="+")
        except Exception:
            pass
        for child in w.winfo_children():
            _bind(child)

    _bind(widget)
