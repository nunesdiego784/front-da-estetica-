"""Catálogo de serviços: cadastro, edição e ativação/desativação."""
import customtkinter as ctk

from components.data_table import Column, DataTable
from components.dialogs import Field, FormDialog
from components.filter_chips import FilterChips
from components.page_header import PageHeader
from components.status_badge import StatusBadge
from components.widgets import action_bar, search_box
from data.repository import RepositoryError
from utils import colors as C
from utils.formatting import brl, format_duration, truncate

from .base_page import BasePage


class ServicesPage(BasePage):
    def build(self) -> None:
        c = self.content
        c.grid_rowconfigure(2, weight=1)
        self.header = PageHeader(c, "Serviços", "Catálogo de serviços, preços e durações.",
                                 actions=[("Novo serviço", lambda: self.open_form(None), "primary", "plus")])
        self.header.grid(row=0, column=0, sticky="ew")
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(18, 12))
        frame, self.search_entry = search_box(bar, "Buscar serviço…", 280, on_change=lambda t: self.refresh())
        frame.grid(row=0, column=0, padx=(0, 16))
        self.chips = FilterChips(bar, [("all", "Todos"), ("active", "Ativos"), ("inactive", "Inativos")],
                                 lambda k: self.refresh(), selected="all")
        self.chips.grid(row=0, column=1)
        self.table = DataTable(c, [
            Column("Serviço", 150, 2, text=lambda s: s.name),
            Column("Descrição", 200, 4, text=lambda s: truncate(s.description or "—", 62), color=C.TEXT_SECONDARY),
            Column("Preço", 100, 0, text=lambda s: brl(s.price_cents)),
            Column("Duração", 80, 0, text=lambda s: format_duration(s.duration_min)),
            Column("Status", 100, 0, render=lambda p, s: StatusBadge(p, "active" if s.active else "inactive")),
            Column("Ações", 80, 0, render=lambda p, s: action_bar(p, [
                ("edit", lambda b, s=s: self.open_form(s), False),
                ("power", lambda b, s=s: self.toggle(s), s.active)])),
        ], empty_text="Nenhum serviço encontrado.")
        self.table.grid(row=2, column=0, sticky="nsew")

    def refresh(self) -> None:
        rows = self.repo.list_services(self.search_text(), self.chips.value or "all")
        self.table.set_rows(rows)
        self.header.set_subtitle(f"{len(rows)} serviço(s) · preços e durações vêm deste catálogo.")

    def open_form(self, service) -> None:
        initial = {"active": True}
        if service:
            initial = dict(service.__dict__, price=f"{service.price_cents / 100:.2f}".replace(".", ","),
                           duration=service.duration_min)

        def submit(vals):
            self.repo.save_service(vals, service.id if service else None)
            self.app.toast.show("Serviço atualizado." if service else "Serviço cadastrado.")

        fields = [Field("name", "Nome do serviço"), Field("description", "Descrição", "multiline", required=False),
                  Field("price", "Preço (R$)", placeholder="150,00"),
                  Field("duration", "Duração estimada (minutos)", placeholder="90"),
                  Field("active", "Disponível para agendamento", "check")]
        FormDialog(self.app, "Editar serviço" if service else "Novo serviço", fields, submit, initial)

    def toggle(self, service) -> None:
        was_active = service.active
        try:
            self.repo.set_service_active(service.id, not was_active)
        except RepositoryError as exc:
            self.app.toast.show(str(exc), "error")
            return
        self.app.toast.show("Serviço desativado." if was_active else "Serviço reativado.", "success")
