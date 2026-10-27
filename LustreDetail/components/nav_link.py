"""Item de navegação do menu superior (texto + linha inferior âmbar quando ativo)."""
from typing import Callable

import customtkinter as ctk

from utils import colors as C
from utils.animation import animate_color
from utils.fonts import text_font


class NavLink(ctk.CTkFrame):
    """Botão de texto com transição suave de cor no hover e sublinhado ativo."""

    def __init__(self, master, text: str, command: Callable, active: bool = False):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.active = active
        self._color = C.TEXT_SECONDARY
        self.grid_rowconfigure(0, weight=1)
        self.button = ctk.CTkButton(
            self, text=text, command=command, width=int(len(text) * 7.6 + 22), height=58,
            fg_color="transparent", hover=False, corner_radius=0, font=text_font(13, "bold"),
            text_color=C.TEXT_SECONDARY)
        self.button.grid(row=0, column=0)
        self.underline = ctk.CTkFrame(self, height=2, corner_radius=0, fg_color="transparent")
        self.underline.grid(row=1, column=0, sticky="ew", padx=10)
        self.button.bind("<Enter>", lambda e: self._hover(True), add="+")
        self.button.bind("<Leave>", lambda e: self._hover(False), add="+")
        self.set_active(active)

    def _apply(self, color: str) -> None:
        self._color = color
        self.button.configure(text_color=color)

    def _hover(self, inside: bool) -> None:
        if self.active:
            return
        target = C.TEXT if inside else C.TEXT_SECONDARY
        animate_color(self, self._apply, self._color, target)

    def set_active(self, active: bool) -> None:
        """Marca/desmarca como página atual."""
        self.active = active
        self._apply(C.ACCENT if active else C.TEXT_SECONDARY)
        self.underline.configure(fg_color=C.ACCENT if active else "transparent")
