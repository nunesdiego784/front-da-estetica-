"""Estoque: produtos, entradas, saídas, histórico e aviso de estoque baixo."""
import customtkinter as ctk

from components.data_table import Column, DataTable
from components.dialogs import Field, FormDialog
from components.filter_chips import FilterChips
from components.page_header import PageHeader
from components.status_badge import StatusBadge
from components.widgets import action_bar, label, search_box
from data.models import PRODUCT_CATEGORIES, UNITS
from utils import colors as C
from utils.formatting import brl, format_quantity, truncate

from .base_page import BasePage


class InventoryPage(BasePage):
    def build(self) -> None:
        c = self.content
        c.grid_rowconfigure(3, weight=1)
        self.header = PageHeader(c, "Estoque", "Produtos usados na operação.",
                                 actions=[("Novo produto", lambda: self.open_product(None), "primary", "plus")])
        self.header.grid(row=0, column=0, sticky="ew")
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(18, 8))
        frame, self.search_entry = search_box(bar, "Buscar produto ou categoria…", 280,
                                              on_change=lambda t: self.refresh())
        frame.grid(row=0, column=0, padx=(0, 16))
        self.chips = FilterChips(bar, [("products", "Produtos"), ("low", "Estoque baixo"),
                                       ("movements", "Movimentações")], self._on_view, selected="products")
        self.chips.grid(row=0, column=1)
        self.banner = label(c, "", 12, C.ACCENT, height=22)
        self.banner.grid(row=2, column=0, sticky="w", pady=(0, 8))

        self.products = DataTable(c, [
            Column("Produto", 170, 3, text=lambda p: truncate(p.name, 34)),
            Column("Categoria", 100, 1, text=lambda p: p.category, color=C.TEXT_SECONDARY),
            Column("Quantidade", 100, 1, text=lambda p: f"{format_quantity(p.quantity)} {p.unit}"),
            Column("Mínimo", 90, 0, text=lambda p: f"{format_quantity(p.min_stock)} {p.unit}", color=C.TEXT_SECONDARY),
            Column("Custo unit.", 90, 0, text=lambda p: brl(p.unit_cost_cents)),
            Column("Situação", 120, 0, render=lambda par, p: StatusBadge(par, "low" if self.repo.is_low(p) else "ok")),
            Column("Ações", 110, 0, render=lambda par, p: action_bar(par, [
                ("arrow_down", lambda b, p=p: self.move(p, "in"), False),
                ("arrow_up", lambda b, p=p: self.move(p, "out"), False),
                ("edit", lambda b, p=p: self.open_product(p), False)])),
        ], empty_text="Nenhum produto encontrado.")
        self.movements = DataTable(c, [
            Column("Data/hora", 130, 0, text=lambda m: f"{m.date[8:10]}/{m.date[5:7]}/{m.date[:4]} {m.date[11:16]}"),
            Column("Produto", 170, 3, text=lambda m: truncate(self._pname(m.product_id), 34)),
            Column("Tipo", 100, 0, render=lambda par, m: StatusBadge(par, m.kind)),
            Column("Quantidade", 110, 1, text=lambda m: f"{format_quantity(m.quantity)} {self._unit(m.product_id)}"),
            Column("Observação", 160, 3, text=lambda m: truncate(m.note or "—", 50), color=C.TEXT_SECONDARY),
        ], empty_text="Nenhuma movimentação registrada.")
        self.products.grid(row=3, column=0, sticky="nsew")
        self.movements.grid(row=3, column=0, sticky="nsew")
        self.movements.grid_remove()

    def _pname(self, pid) -> str:
        p = self.repo.get_product(pid)
        return p.name if p else "—"

    def _unit(self, pid) -> str:
        p = self.repo.get_product(pid)
        return p.unit if p else ""

    def _on_view(self, _key) -> None:
        self.refresh()

    def refresh(self) -> None:
        view = self.chips.value
        low = self.repo.low_stock_products()
        self.banner.configure(text=f"⚠ {len(low)} produto(s) com estoque baixo: "
                                   f"{', '.join(p.name for p in low[:3])}{'…' if len(low) > 3 else ''}" if low else "")
        if view == "movements":
            self.products.grid_remove()
            self.movements.grid()
            rows = self.repo.list_movements(self.search_text())
            self.movements.set_rows(rows)
        else:
            self.movements.grid_remove()
            self.products.grid()
            rows = self.repo.list_products(self.search_text(), only_low=(view == "low"))
            self.products.set_rows(rows)
        self.header.set_subtitle(f"{len(rows)} registro(s) · {len(self.repo.products)} produto(s) no total.")

    def open_product(self, product) -> None:
        initial = {}
        if product:
            initial = dict(product.__dict__, min_stock=format_quantity(product.min_stock),
                           unit_cost=f"{product.unit_cost_cents / 100:.2f}".replace(".", ","))

        def submit(vals):
            self.repo.save_product(vals, product.id if product else None)
            self.app.toast.show("Produto atualizado." if product else "Produto cadastrado.")

        fields = [Field("name", "Nome do produto"),
                  Field("category", "Categoria", "choice", [(c, c) for c in PRODUCT_CATEGORIES]),
                  Field("unit", "Unidade de medida", "choice", [(u, u) for u in UNITS])]
        if not product:
            fields.append(Field("quantity", "Quantidade inicial", placeholder="0", required=False,
                                hint="Gera automaticamente uma entrada no histórico."))
        fields += [Field("min_stock", "Estoque mínimo", placeholder="0"),
                   Field("unit_cost", "Custo unitário (R$)", placeholder="0,00")]
        FormDialog(self.app, "Editar produto" if product else "Novo produto", fields, submit, initial)

    def move(self, product, kind: str) -> None:
        title = "Entrada de produto" if kind == "in" else "Saída de produto"

        def submit(vals):
            self.repo.move_stock(product.id, kind, vals["quantity"], vals["note"])
            self.app.toast.show("Entrada registrada." if kind == "in" else "Saída registrada.")

        FormDialog(self.app, title,
                   [Field("quantity", f"Quantidade ({product.unit})", placeholder="1"),
                    Field("note", "Observação", required=False)],
                   submit, submit_text="Registrar",
                   subtitle=f"{product.name} · disponível: {format_quantity(product.quantity)} {product.unit}")
