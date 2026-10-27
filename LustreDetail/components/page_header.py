"""Cabeçalho de página: título, subtítulo e ações principais."""
import customtkinter as ctk

from utils import colors as C

from .widgets import button, label


class PageHeader(ctk.CTkFrame):
    """Título (Barlow Condensed), subtítulo, texto à direita e botões de ação.

    ``actions``: lista de tuplas ``(texto, comando, tipo, icone)``.
    """

    def __init__(self, master, title: str, subtitle: str = "", actions=None, right_text: str = ""):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        label(left, title, 34, C.TEXT, "bold", display=True, height=44).pack(anchor="w")
        self.subtitle = label(left, subtitle, 13, C.TEXT_SECONDARY, height=22)
        self.subtitle.pack(anchor="w")

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        self.right_label = label(right, right_text, 13, C.TEXT_SECONDARY, anchor="e", height=22)
        self.right_label.pack(side="left", padx=(0, 16))
        self.buttons = []
        for text, command, kind, icon in (actions or []):
            btn = button(right, text, command, kind or "primary", icon=icon)
            btn.pack(side="left", padx=(8, 0))
            self.buttons.append(btn)

    def set_right_text(self, text: str) -> None:
        self.right_label.configure(text=text)

    def set_subtitle(self, text: str) -> None:
        self.subtitle.configure(text=text)
