"""Filtros rápidos em formato de 'chips' (seleção única)."""
from typing import Callable, Optional

import customtkinter as ctk

from utils import colors as C
from utils.fonts import text_font


class FilterChips(ctk.CTkFrame):
    """Linha de chips; ``command(chave)`` é chamado quando o usuário troca a seleção."""

    def __init__(self, master, options, command: Optional[Callable] = None, selected=None):
        super().__init__(master, fg_color="transparent")
        self._command = command
        self._buttons = {}
        self.value = selected if selected is not None else options[0][0]
        for i, (key, text) in enumerate(options):
            btn = ctk.CTkButton(self, text=text, width=int(len(text) * 7.4 + 28), height=28,
                                corner_radius=14, font=text_font(12),
                                command=lambda k=key: self.select(k, notify=True))
            btn.grid(row=0, column=i, padx=(0, 6))
            self._buttons[key] = btn
        self._restyle()

    def _restyle(self) -> None:
        for key, btn in self._buttons.items():
            if key == self.value:
                btn.configure(fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER, text_color=C.BG,
                              border_width=0)
            else:
                btn.configure(fg_color="transparent", hover_color=C.SURFACE_HOVER,
                              text_color=C.TEXT_SECONDARY, border_width=1, border_color=C.BORDER)

    def select(self, key, notify: bool = False) -> None:
        """Seleciona um chip; ``notify`` dispara o callback."""
        if key not in self._buttons:
            return
        changed = key != self.value
        self.value = key
        self._restyle()
        if notify and self._command and changed:
            self._command(key)

    def clear_selection(self) -> None:
        """Deixa nenhum chip selecionado (ex.: quando outro filtro assume o controle)."""
        self.value = None
        self._restyle()
