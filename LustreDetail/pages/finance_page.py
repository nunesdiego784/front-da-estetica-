"""Financeiro: receitas, despesas, saldo, serviços pagos e pendentes.

Somente valores EFETIVAMENTE recebidos/pagos entram nos totais. Serviços
concluídos e não pagos aparecem em 'A receber', separados do saldo.
"""
import customtkinter as ctk

from components.data_table import Column, DataTable
from components.dialogs import Field, FormDialog
from components.filter_chips import FilterChips
from components.page_header import PageHeader
from components.plate_tag import PlateTag
from components.stat_strip import StatData, StatStrip
from components.widgets import button, combo, label, search_box
from data.models import EXPENSE_CATEGORIES, PAYMENT_METHODS
from utils import colors as C
from utils.formatting import brl, format_date_br, format_plate, truncate

from .base_page import BasePage

PERIODS = [("today", "Hoje"), ("7d", "7 dias"), ("month", "Mês atual"), ("all", "Tudo")]
PERIOD_NAMES = {"today": "hoje", "7d": "últimos 7 dias", "month": "mês atual", "all": "todo o período"}
VIEWS = [("entries", "Movimentações"), ("pending", "Serviços pendentes"), ("paid", "Serviços pagos")]


class FinancePage(BasePage):
    def build(self) -> None:
        c = self.content
        c.grid_rowconfigure(3, weight=1)
        self.header = PageHeader(c, "Financeiro", "Receitas, despesas e recebimentos.", actions=[
            ("Registrar recebimento", lambda: self.add_entry("income"), "primary", "plus"),
            ("Registrar despesa", lambda: self.add_entry("expense"), "ghost", "plus")])
        self.header.grid(row=0, column=0, sticky="ew")
        self.stats = StatStrip(c)
        self.stats.grid(row=1, column=0, sticky="ew", pady=(18, 0))

        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", pady=(16, 12))
        self.period_chips = FilterChips(bar, PERIODS, lambda k: self.refresh(), selected="month")
        self.period_chips.grid(row=0, column=0, padx=(0, 14))
        self.method_cb = combo(bar, ["Todas as formas"] + PAYMENT_METHODS, command=lambda v: self.refresh(), width=170)
        self.method_cb.grid(row=0, column=1, padx=(0, 14))
        frame, self.search_entry = search_box(bar, "Buscar…", 200, on_change=lambda t: self.refresh())
        frame.grid(row=0, column=2, padx=(0, 14))
        self.view_chips = FilterChips(bar, VIEWS, lambda k: self.refresh(), selected="entries")
        self.view_chips.grid(row=0, column=3)

        self.entries = DataTable(c, [
            Column("Data", 90, 0, text=lambda e: format_date_br(e.date)),
            Column("Descrição", 200, 4, text=lambda e: truncate(e.description, 52)),
            Column("Categoria", 100, 1, text=lambda e: e.category or "—", color=C.TEXT_SECONDARY),
            Column("Forma", 130, 1, text=lambda e: e.method or "—", color=C.TEXT_SECONDARY),
            Column("Valor", 120, 0, render=self._cell_amount),
        ], empty_text="Nenhuma movimentação no período.")
        self.pending = DataTable(c, [
            Column("Serviço em", 90, 0, text=lambda v: format_date_br(v.appt.date)),
            Column("Cliente", 150, 2, text=lambda v: truncate(v.client_name, 26)),
            Column("Serviço", 150, 2, text=lambda v: truncate(v.service_name, 26)),
            Column("Veículo", 110, 0, render=lambda p, v: PlateTag(p, v.plate)),
            Column("Valor", 110, 0, text=lambda v: brl(v.appt.price_cents)),
            Column("Ação", 120, 0, render=lambda p, v: button(p, "Receber", lambda v=v: self.app.appt_actions.pay(v),
                                                                "primary", icon="coin", size=12, height=30)),
        ], empty_text="Nenhum serviço aguardando pagamento.")
        self.paid = DataTable(c, [
            Column("Pago em", 90, 0, text=lambda v: format_date_br(v.appt.paid_date)),
            Column("Cliente", 150, 2, text=lambda v: truncate(v.client_name, 26)),
            Column("Serviço", 150, 2, text=lambda v: truncate(v.service_name, 26)),
            Column("Placa", 100, 0, text=lambda v: format_plate(v.plate)),
            Column("Forma", 130, 1, text=lambda v: v.appt.payment_method),
            Column("Valor", 110, 0, text=lambda v: brl(v.appt.price_cents)),
        ], empty_text="Nenhum serviço pago no período.")
        self._tables = {"entries": self.entries, "pending": self.pending, "paid": self.paid}
        for t in self._tables.values():
            t.grid(row=3, column=0, sticky="nsew")
            t.grid_remove()

    def _cell_amount(self, parent, e):
        sign, color = ("+", C.SUCCESS) if e.kind == "income" else ("−", C.DANGER)
        return label(parent, f"{sign} {brl(e.amount_cents)}", 13, color, "bold")

    def _method(self):
        v = self.method_cb.get()
        return v if v in PAYMENT_METHODS else None

    def refresh(self) -> None:
        repo, period = self.repo, self.period_chips.value or "month"
        start, end = repo.period_range(period)
        method, search = self._method(), self.search_text()
        s = repo.finance_summary(start, end, method)
        name = PERIOD_NAMES[period]
        pending = repo.pending_receivables()
        self.stats.update_stats([
            StatData("Receitas", brl(s["income"]), f"Recebido · {name}", "", "positive"),
            StatData("Despesas", brl(s["expense"]), f"Pago · {name}"),
            StatData("Saldo do período", brl(s["balance"]), "Receitas − despesas",
                     "Negativo" if s["balance"] < 0 else "", "negative"),
            StatData("A receber", brl(repo.pending_total()), f"{len(pending)} serviço(s) concluído(s) sem pagamento",
                     "Não incluído no saldo", "warning"),
        ])
        view = self.view_chips.value or "entries"
        for key, table in self._tables.items():
            (table.grid if key == view else table.grid_remove)()
        if view == "entries":
            rows = repo.list_entries(start, end, method, search)
        elif view == "pending":
            rows = repo.pending_receivables(search)
        else:
            rows = repo.paid_services(start, end, method, search)
        self._tables[view].set_rows(rows)
        self.header.set_subtitle(f"{len(rows)} registro(s) na visualização atual.")

    def add_entry(self, kind: str) -> None:
        income = kind == "income"

        def submit(vals):
            self.repo.add_entry(kind, vals)
            self.app.toast.show("Recebimento registrado." if income else "Despesa registrada.")

        fields = [Field("description", "Descrição"), Field("amount", "Valor (R$)", placeholder="120,00"),
                  Field("method", "Forma de pagamento", "choice", [(m, m) for m in PAYMENT_METHODS]),
                  Field("date", "Data", required=False, placeholder="vazio = hoje", hint="Formato DD/MM/AAAA.")]
        if not income:
            fields.insert(3, Field("category", "Categoria", "choice", [(c, c) for c in EXPENSE_CATEGORIES]))
        FormDialog(self.app, "Registrar recebimento" if income else "Registrar despesa", fields, submit,
                   subtitle="Receita avulsa, sem vínculo com agendamento." if income else "")
