"""Divisória discreta (linha fina) horizontal ou vertical."""
import customtkinter as ctk

from utils import colors as C


class Divider(ctk.CTkFrame):
    """Linha de 1 px na cor de borda do tema."""

    def __init__(self, master, orientation: str = "horizontal", color: str = C.BORDER):
        if orientation == "vertical":
            super().__init__(master, width=1, fg_color=color, corner_radius=0)
        else:
            super().__init__(master, height=1, fg_color=color, corner_radius=0)
