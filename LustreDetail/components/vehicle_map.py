"""Mapa visual interativo do veículo (vista de cima), desenhado com Pillow.

O desenho e as máscaras ficam em ``utils.car_drawing`` (sem Tkinter). Este
widget apenas exibe a imagem em um ``tk.Canvas`` e traduz o mouse em regiões:
hover destaca, clique seleciona/desmarca, e regiões com serviço em andamento
recebem um ponto âmbar.
"""
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk
from PIL import ImageTk

from utils import colors as C
from utils.car_drawing import CarRenderer
from utils.theme import scaling


class VehicleMap(ctk.CTkFrame):
    """Carro visto de cima com regiões clicáveis (capô, teto, porta-malas, laterais)."""

    def __init__(self, master, width: int = 170, on_select: Optional[Callable] = None,
                 on_hover: Optional[Callable] = None, bg: str = C.SURFACE):
        super().__init__(master, fg_color="transparent")
        self._on_select, self._on_hover = on_select, on_hover
        self.selected: Optional[str] = None
        self.hover: Optional[str] = None
        self.active: frozenset = frozenset()
        self._photos: dict = {}

        px = max(60, int(width * scaling(self)))
        self.renderer = CarRenderer(px, bg)
        self.canvas = tk.Canvas(self, width=self.renderer.out_w, height=self.renderer.out_h,
                                bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack()
        self._image_id = self.canvas.create_image(0, 0, anchor="nw")
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", self._leave)
        self.canvas.bind("<Button-1>", self._click)
        self._draw()

    # ------------------------------------------------------------ interações
    def _motion(self, event) -> None:
        region = self.renderer.hit_test(event.x, event.y)
        if region != self.hover:
            self.hover = region
            self.canvas.configure(cursor="hand2" if region else "arrow")
            self._draw()
            if self._on_hover:
                self._on_hover(region)

    def _leave(self, _event) -> None:
        if self.hover is not None:
            self.hover = None
            self.canvas.configure(cursor="arrow")
            self._draw()
            if self._on_hover:
                self._on_hover(None)

    def _click(self, event) -> None:
        region = self.renderer.hit_test(event.x, event.y)
        if region:
            self.select(None if region == self.selected else region, notify=True)

    # --------------------------------------------------------------- API
    def select(self, region: Optional[str], notify: bool = False) -> None:
        """Seleciona uma região (ou ``None`` para limpar)."""
        self.selected = region
        self._draw()
        if notify and self._on_select:
            self._on_select(region)

    def set_active(self, regions) -> None:
        """Regiões com serviço em andamento (ganham destaque discreto e um ponto)."""
        regions = frozenset(r for r in regions if r)
        if regions != self.active:
            self.active = regions
            self._draw()

    # --------------------------------------------------------------- desenho
    def _draw(self) -> None:
        key = (self.selected, self.hover, self.active)
        photo = self._photos.get(key)
        if photo is None:
            if len(self._photos) > 40:
                self._photos.clear()
            photo = ImageTk.PhotoImage(
                self.renderer.render(self.selected, self.hover, self.active), master=self.canvas)
            self._photos[key] = photo
        self._current = photo  # mantém referência (evita coleta pelo Tk)
        self.canvas.itemconfigure(self._image_id, image=photo)
