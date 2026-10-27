"""Popover: menus e painéis flutuantes simples ancorados a um widget.

O painel é um frame posicionado sobre a janela principal (sem criar janelas
extras). Fecha ao clicar fora, ao escolher uma opção ou com Esc.
"""
from typing import Callable, Optional

import customtkinter as ctk

from utils import colors as C
from utils.fonts import text_font
from utils.theme import RADIUS, scaling


class PopoverManager:
    """Controla um único popover aberto por vez."""

    def __init__(self, app):
        self.app = app
        self._frame: Optional[ctk.CTkFrame] = None
        self._anchor = None
        app.bind_all("<Button-1>", self._on_click, add="+")

    @property
    def is_open(self) -> bool:
        return self._frame is not None

    def close(self) -> bool:
        """Fecha o popover aberto. Devolve True se havia algum."""
        if self._frame is None:
            return False
        try:
            self._frame.destroy()
        except Exception:
            pass
        self._frame, self._anchor = None, None
        return True

    # --------------------------------------------------------------- abertura
    def show_custom(self, anchor, builder: Callable, width: int = 300, align: str = "left",
                    toggle: bool = True) -> None:
        """Abre um painel; ``builder(frame)`` preenche o conteúdo (largura fixa ``width``)."""
        if toggle and self._anchor is anchor and self._frame is not None:
            self.close()
            return
        self.close()
        frame = ctk.CTkFrame(self.app, fg_color=C.SURFACE, border_width=1, border_color=C.BORDER,
                             corner_radius=RADIUS)
        builder(frame)
        self._frame, self._anchor = frame, anchor
        self.app.update_idletasks()
        scale = scaling(self.app)
        ax = anchor.winfo_rootx() - self.app.winfo_rootx()
        ay = anchor.winfo_rooty() - self.app.winfo_rooty() + anchor.winfo_height() + 6
        x = ax / scale if align == "left" else (ax + anchor.winfo_width()) / scale - width
        x = max(8, min(x, self.app.winfo_width() / scale - width - 8))
        frame.place(x=x, y=ay / scale)
        frame.lift()

    def show_menu(self, anchor, items, width: int = 220, align: str = "right") -> None:
        """Menu de opções. ``items``: lista de ``(texto, comando)`` ou ``(texto, comando, perigo)``."""

        def build(frame):
            for i, item in enumerate(items):
                text, command = item[0], item[1]
                danger = len(item) > 2 and item[2]
                btn = ctk.CTkButton(
                    frame, text=text, width=width - 12, height=32, anchor="w", corner_radius=6,
                    fg_color="transparent", hover_color=C.SURFACE_HOVER, font=text_font(13),
                    text_color=C.DANGER if danger else C.TEXT,
                    command=lambda c=command: self._choose(c))
                btn.grid(row=i, column=0, padx=6, pady=(6 if i == 0 else 0, 6 if i == len(items) - 1 else 2))

        self.show_custom(anchor, build, width, align)

    def _choose(self, command: Callable) -> None:
        self.close()
        self.app.after(10, command)

    # --------------------------------------------------------- clique externo
    def _on_click(self, event) -> None:
        if self._frame is None:
            return
        target = str(event.widget)
        if target.startswith(str(self._frame)):
            return
        if self._anchor is not None and target.startswith(str(self._anchor)):
            return  # o próprio âncora decide (alterna abrir/fechar)
        self.close()
