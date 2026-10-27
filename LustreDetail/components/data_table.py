"""Tabela genérica paginada, montada com widgets do CustomTkinter em linhas/colunas.

* O número de linhas por página se ajusta à altura disponível (ou é fixo).
* Cada coluna define como desenhar a célula (texto simples ou um widget).
* Hover na linha, divisórias finas e paginador discreto.
"""
from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

from utils import colors as C
from utils.theme import RADIUS, scaling

from .divider import Divider
from .widgets import bind_hover, caption, icon_button, label


@dataclass
class Column:
    """Definição de coluna.

    ``text(row)`` devolve o texto da célula; ``render(parent, row)`` devolve um
    widget pronto (será posicionado pela tabela). Informe um dos dois.
    """
    header: str
    width: int = 100
    weight: int = 0
    text: Optional[Callable] = None
    render: Optional[Callable] = None
    color: str = C.TEXT


class DataTable(ctk.CTkFrame):
    """Tabela com cabeçalho, linhas, estado vazio e paginação."""

    def __init__(self, master, columns, row_height: int = 48, page_size: Optional[int] = None,
                 empty_text: str = "Nenhum registro encontrado.", show_pager: bool = True):
        super().__init__(master, fg_color=C.SURFACE, border_width=1, border_color=C.BORDER,
                         corner_radius=RADIUS)
        self.columns = columns
        self.row_height = row_height
        self.empty_text = empty_text
        self.show_pager = show_pager
        self._auto = page_size is None
        self._page_size = page_size or 8
        self._rows: list = []
        self._page = 0
        self._render_job = None
        self._widgets: list = []

        self.grid_columnconfigure(0, weight=1)
        self._header = ctk.CTkFrame(self, fg_color="transparent", height=36)
        self._header.grid(row=0, column=0, sticky="ew", padx=1, pady=(1, 0))
        self._header.grid_propagate(False)
        self._header.grid_rowconfigure(0, weight=1)
        self._config_columns(self._header)
        for i, col in enumerate(columns):
            caption(self._header, col.header).grid(row=0, column=i, sticky="w",
                                                   padx=(14 if i == 0 else 6, 6))
        Divider(self).grid(row=1, column=0, sticky="ew", padx=1)

        self._body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        if self._auto:
            self.grid_rowconfigure(2, weight=1)
            self._body.grid(row=2, column=0, sticky="nsew", padx=1)
            self._body.bind("<Configure>", self._on_body_configure)
        else:
            self._body.configure(height=self._page_size * (row_height + 1))
            self._body.grid(row=2, column=0, sticky="ew", padx=1)
        self._body.grid_propagate(False)
        self._body.grid_columnconfigure(0, weight=1)

        self._pager = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self._pager.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 2))
        self._pager.grid_columnconfigure(0, weight=1)
        self._count_label = label(self._pager, "", 12, C.TEXT_SECONDARY, height=28)
        self._count_label.grid(row=0, column=0, sticky="w")
        self._prev = icon_button(self._pager, "chevron_left", self._go_prev, size=28)
        self._page_label = label(self._pager, "", 12, C.TEXT_SECONDARY, anchor="center", height=28, width=60)
        self._next = icon_button(self._pager, "chevron_right", self._go_next, size=28)
        self._prev.grid(row=0, column=1)
        self._page_label.grid(row=0, column=2)
        self._next.grid(row=0, column=3)
        if not show_pager:
            self._pager.grid_remove()

    # ---------------------------------------------------------------- layout
    def _config_columns(self, frame) -> None:
        for i, col in enumerate(self.columns):
            frame.grid_columnconfigure(i, weight=col.weight, minsize=col.width)

    def _on_body_configure(self, event) -> None:
        if event.height < 20:
            return
        size = max(3, int(event.height / (scaling(self) * (self.row_height + 1))))
        if size != self._page_size:
            self._page_size = size
            self._schedule_render()

    def _schedule_render(self) -> None:
        if self._render_job is None:
            self._render_job = self.after(30, self._render)

    # ------------------------------------------------------------------ dados
    def set_rows(self, rows, keep_page: bool = False) -> None:
        """Define as linhas a exibir (lista de objetos quaisquer)."""
        self._rows = list(rows)
        if not keep_page:
            self._page = 0
        self._render()

    @property
    def total_pages(self) -> int:
        return max(1, -(-len(self._rows) // self._page_size))

    def _go_prev(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._render()

    def _go_next(self) -> None:
        if self._page < self.total_pages - 1:
            self._page += 1
            self._render()

    # ------------------------------------------------------------- renderização
    def _render(self) -> None:
        self._render_job = None
        for w in self._widgets:
            w.destroy()
        self._widgets = []
        self._page = min(self._page, self.total_pages - 1)
        start = self._page * self._page_size
        page_rows = self._rows[start:start + self._page_size]

        if not page_rows:
            empty = label(self._body, self.empty_text, 13, C.TEXT_MUTED, anchor="center", height=40)
            empty.grid(row=0, column=0, sticky="ew", pady=40)
            self._widgets.append(empty)
        for i, row in enumerate(page_rows):
            self._build_row(i, row)

        total = len(self._rows)
        if total:
            self._count_label.configure(
                text=f"Mostrando {start + 1}–{start + len(page_rows)} de {total}")
        else:
            self._count_label.configure(text="0 registros")
        pages = self.total_pages
        self._page_label.configure(text=f"{self._page + 1} / {pages}")
        state_prev = "normal" if self._page > 0 else "disabled"
        state_next = "normal" if self._page < pages - 1 else "disabled"
        self._prev.configure(state=state_prev)
        self._next.configure(state=state_next)

    def _build_row(self, i: int, row) -> None:
        rf = ctk.CTkFrame(self._body, fg_color="transparent", height=self.row_height, corner_radius=0)
        rf.grid(row=i * 2, column=0, sticky="ew")
        rf.grid_propagate(False)
        rf.grid_rowconfigure(0, weight=1)
        self._config_columns(rf)
        for ci, col in enumerate(self.columns):
            padx = (14 if ci == 0 else 6, 6)
            if col.render:
                widget = col.render(rf, row)
            else:
                widget = label(rf, str(col.text(row)), 13, col.color)
            widget.grid(row=0, column=ci, sticky="w", padx=padx)
        div = Divider(self._body)
        div.grid(row=i * 2 + 1, column=0, sticky="ew")
        bind_hover(rf, lambda f=rf: f.configure(fg_color=C.SURFACE_HOVER),
                   lambda f=rf: f.configure(fg_color="transparent"))
        self._widgets.extend([rf, div])
