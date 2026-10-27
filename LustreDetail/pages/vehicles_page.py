"""Veículos: cadastro vinculado a clientes, busca e histórico de serviços."""
import customtkinter as ctk

from components.data_table import Column, DataTable
from components.dialogs import ConfirmDialog, Field, FormDialog, InfoDialog
from components.page_header import PageHeader
from components.plate_tag import PlateTag
from components.widgets import action_bar, label, search_box
from data.repository import RepositoryError
from utils import colors as C
from utils.formatting import brl, format_date_br, format_plate, truncate
from utils.theme import STATUS_STYLES

from .base_page import BasePage


class VehiclesPage(BasePage):
    def build(self) -> None:
        c = self.content
        c.grid_rowconfigure(2, weight=1)
        self.header = PageHeader(c, "Veículos", "Veículos cadastrados e seu histórico de serviços.",
                                 actions=[("Novo veículo", lambda: self.open_form(None), "primary", "plus")])
        self.header.grid(row=0, column=0, sticky="ew")
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(18, 12))
        frame, self.search_entry = search_box(bar, "Buscar por placa, modelo, cor ou cliente…", 340,
                                              on_change=lambda t: self.refresh())
        frame.grid(row=0, column=0)
        self.table = DataTable(c, [
            Column("Placa", 110, 0, render=lambda p, v: PlateTag(p, v.plate)),
            Column("Veículo", 170, 2, text=lambda v: truncate(f"{v.brand} {v.model} · {v.year}", 32)),
            Column("Cor", 90, 1, text=lambda v: v.color),
            Column("Cliente", 160, 2, text=lambda v: truncate(self._owner(v), 28)),
            Column("Serviços", 70, 0, text=lambda v: len(self.repo.vehicle_appointments(v.id))),
            Column("Ações", 110, 0, render=lambda p, v: action_bar(p, [
                ("clock", lambda b, v=v: self.history(v), False),
                ("edit", lambda b, v=v: self.open_form(v), False),
                ("trash", lambda b, v=v: self.delete(v), True)])),
        ], empty_text="Nenhum veículo encontrado.")
        self.table.grid(row=2, column=0, sticky="nsew")

    def _owner(self, v) -> str:
        c = self.repo.get_client(v.client_id)
        return c.name if c else "—"

    def refresh(self) -> None:
        rows = self.repo.list_vehicles(self.search_text())
        self.table.set_rows(rows)
        self.header.set_subtitle(f"{len(rows)} veículo(s) cadastrado(s).")

    def open_form(self, vehicle) -> None:
        clients = [c for c in self.repo.list_clients() if c.active or (vehicle and c.id == vehicle.client_id)]
        if not clients:
            self.app.toast.show("Cadastre um cliente antes de cadastrar veículos.", "warning")
            return
        initial = dict(vehicle.__dict__) if vehicle else {}
        if vehicle:
            initial["plate"] = format_plate(vehicle.plate)

        def submit(vals):
            self.repo.save_vehicle(vals, vehicle.id if vehicle else None)
            self.app.toast.show("Veículo atualizado." if vehicle else "Veículo cadastrado.")

        fields = [Field("client_id", "Cliente responsável", "choice", [(c.id, f"{c.name} · {c.phone}") for c in clients]),
                  Field("brand", "Marca"), Field("model", "Modelo"),
                  Field("year", "Ano", placeholder="2021"), Field("color", "Cor"),
                  Field("plate", "Placa", placeholder="ABC1D23 ou ABC-1234")]
        FormDialog(self.app, "Editar veículo" if vehicle else "Novo veículo", fields, submit, initial)

    def history(self, vehicle) -> None:
        views = self.repo.vehicle_history(vehicle.id)
        rows = [("Veículo", f"{vehicle.brand} {vehicle.model} {vehicle.year} · {vehicle.color}"),
                ("Placa", format_plate(vehicle.plate)), ("Cliente", self._owner(vehicle)),
                ("Serviços", str(len(views)))]

        def extra(parent):
            box = ctk.CTkScrollableFrame(parent, fg_color=C.BG, height=210, corner_radius=6,
                                         border_width=1, border_color=C.BORDER)
            box.grid(row=0, column=0, sticky="ew")
            box.grid_columnconfigure(0, weight=1)
            if not views:
                label(box, "Sem serviços registrados para este veículo.", 13, C.TEXT_MUTED, height=30
                      ).grid(row=0, column=0, pady=20)
            for i, v in enumerate(views):
                status = STATUS_STYLES[v.appt.status][0].replace("● ", "")
                label(box, f"{format_date_br(v.appt.date)} {v.appt.time} · {v.service_name} · {status} · "
                           f"{brl(v.appt.price_cents)}", 12, C.TEXT, height=22).grid(row=i, column=0, sticky="w", padx=8, pady=2)

        InfoDialog(self.app, "Histórico de serviços", rows, extra=extra, extra_height=230)

    def delete(self, vehicle) -> None:
        def go():
            try:
                self.repo.delete_vehicle(vehicle.id)
                self.app.toast.show("Veículo excluído.")
            except RepositoryError as exc:
                self.app.toast.show(str(exc), "warning", 6000)

        ConfirmDialog(self.app, "Excluir veículo",
                      f"Excluir {vehicle.brand} {vehicle.model} ({format_plate(vehicle.plate)})? "
                      "Veículos com histórico de serviços não podem ser excluídos.", go, confirm_text="Excluir")
