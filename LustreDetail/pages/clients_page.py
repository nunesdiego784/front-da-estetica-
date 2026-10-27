"""Clientes: cadastro, busca, detalhes, edição e exclusão (com proteção do histórico)."""
import customtkinter as ctk

from components.data_table import Column, DataTable
from components.dialogs import ConfirmDialog, Field, FormDialog, InfoDialog
from components.filter_chips import FilterChips
from components.page_header import PageHeader
from components.status_badge import StatusBadge
from components.widgets import action_bar, search_box
from data.repository import RepositoryError
from utils.formatting import format_plate, truncate

from .base_page import BasePage


class ClientsPage(BasePage):
    def build(self) -> None:
        c = self.content
        c.grid_rowconfigure(2, weight=1)
        self.header = PageHeader(c, "Clientes", "Cadastro e histórico de clientes.",
                                 actions=[("Novo cliente", lambda: self.open_form(None), "primary", "plus")])
        self.header.grid(row=0, column=0, sticky="ew")
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(18, 12))
        frame, self.search_entry = search_box(bar, "Buscar por nome, telefone ou e-mail…", 320,
                                              on_change=lambda t: self.refresh())
        frame.grid(row=0, column=0, padx=(0, 16))
        self.chips = FilterChips(bar, [("all", "Todos"), ("active", "Ativos"), ("inactive", "Inativos")],
                                 lambda k: self.refresh(), selected="all")
        self.chips.grid(row=0, column=1)
        self.table = DataTable(c, [
            Column("Nome", 160, 3, text=lambda cl: truncate(cl.name, 32)),
            Column("Telefone", 130, 1, text=lambda cl: cl.phone),
            Column("E-mail", 160, 2, text=lambda cl: truncate(cl.email or "—", 30), color="#8B9098"),
            Column("Veículos", 70, 0, text=lambda cl: len(self.repo.client_vehicles(cl.id))),
            Column("Status", 100, 0, render=lambda p, cl: StatusBadge(p, "active" if cl.active else "inactive")),
            Column("Ações", 110, 0, render=lambda p, cl: action_bar(p, [
                ("eye", lambda b, cl=cl: self.show(cl), False),
                ("edit", lambda b, cl=cl: self.open_form(cl), False),
                ("trash", lambda b, cl=cl: self.delete(cl), True)])),
        ], empty_text="Nenhum cliente encontrado.")
        self.table.grid(row=2, column=0, sticky="nsew")

    def refresh(self) -> None:
        rows = self.repo.list_clients(self.search_text(), self.chips.value or "all")
        self.table.set_rows(rows)
        self.header.set_subtitle(f"{len(rows)} cliente(s) · cadastro e histórico de clientes.")

    def open_form(self, client) -> None:
        initial = client.__dict__ if client else {"active": True}

        def submit(vals):
            self.repo.save_client(vals, client.id if client else None)
            self.app.toast.show("Cliente atualizado." if client else "Cliente cadastrado.")

        fields = [Field("name", "Nome completo"), Field("phone", "Telefone", placeholder="(11) 91234-5678"),
                  Field("email", "E-mail", required=False), Field("notes", "Observações", "multiline", required=False),
                  Field("active", "Cliente ativo", "check")]
        FormDialog(self.app, "Editar cliente" if client else "Novo cliente", fields, submit, initial)

    def show(self, client) -> None:
        vehicles = self.repo.client_vehicles(client.id)
        rows = [("Nome", client.name), ("Telefone", client.phone), ("E-mail", client.email or "—"),
                ("Status", "Ativo" if client.active else "Inativo"),
                ("Veículos", "; ".join(f"{v.brand} {v.model} ({format_plate(v.plate)})" for v in vehicles) or "Nenhum"),
                ("Agendamentos", str(len(self.repo.client_appointments(client.id)))),
                ("Observações", client.notes or "—")]
        InfoDialog(self.app, "Detalhes do cliente", rows)

    def delete(self, client) -> None:
        def go():
            try:
                self.repo.delete_client(client.id)
                self.app.toast.show("Cliente excluído.")
            except RepositoryError as exc:
                self.app.toast.show(str(exc), "warning", 7000)

        ConfirmDialog(self.app, "Excluir cliente", f"Excluir o cadastro de {client.name}? "
                      "Clientes com veículos ou agendamentos não podem ser excluídos.",
                      go, confirm_text="Excluir")
