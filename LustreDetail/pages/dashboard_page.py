"""Dashboard: operação agora, mapa do veículo, indicadores e próximos agendamentos."""
import customtkinter as ctk

from components.appointments_table import AppointmentsTable
from components.page_header import PageHeader
from components.service_item import ServiceItem
from components.stat_strip import StatData, StatStrip
from components.vehicle_map import VehicleMap
from components.widgets import button, card, caption, label
from utils import colors as C
from utils.data_labels import region_label
from utils.formatting import brl, date_long_pt

from .base_page import BasePage

MAX_OPERATION_ITEMS = 4


class DashboardPage(BasePage):
    scrollable = True

    def build(self) -> None:
        c = self.content
        self.header = PageHeader(
            c, "Dashboard", "Visão geral da operação de hoje.",
            actions=[("Novo agendamento", self.app.open_appointment_dialog, "primary", "plus")])
        self.header.grid(row=0, column=0, sticky="ew")
        self.selected_region = None

        # --- linha 1: Operação agora + mapa do veículo ---
        top = ctk.CTkFrame(c, fg_color="transparent")
        top.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        top.grid_columnconfigure(0, weight=1)

        ops = card(top)
        ops.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        ops.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(ops, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        head.grid_columnconfigure(1, weight=1)
        label(head, "Operação agora", 22, C.TEXT, "bold", display=True, height=28).grid(row=0, column=0)
        self.ops_count = label(head, "", 12, C.TEXT_SECONDARY, height=20)
        self.ops_count.grid(row=0, column=1, sticky="w", padx=12)
        self.clear_btn = button(head, "Limpar seleção do mapa", lambda: self._select_region(None),
                                "link", size=12, height=26, width=170)
        self.ops_list = ctk.CTkFrame(ops, fg_color="transparent")
        self.ops_list.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))
        self.ops_list.grid_columnconfigure(0, weight=1)

        map_card = card(top)
        map_card.grid(row=0, column=1, sticky="ns")
        caption(map_card, "Mapa do veículo").pack(anchor="w", padx=18, pady=(16, 0))
        self.map = VehicleMap(map_card, width=170, on_select=self._on_map_select, on_hover=self._on_map_hover)
        self.map.pack(padx=18, pady=(8, 4))
        self.map_caption = label(map_card, "", 13, C.TEXT, "bold", anchor="center", height=22, width=210)
        self.map_caption.pack()
        self.map_hint = label(map_card, "", 11, C.TEXT_SECONDARY, anchor="center", height=32,
                              wraplength=200, justify="center", width=210)
        self.map_hint.pack(pady=(0, 14))

        # --- linha 2: indicadores ---
        self.stats = StatStrip(c)
        self.stats.grid(row=2, column=0, sticky="ew", pady=(16, 0))

        # --- linha 3: próximos agendamentos ---
        up = card(c)
        up.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        up.grid_columnconfigure(0, weight=1)
        uh = ctk.CTkFrame(up, fg_color="transparent")
        uh.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        uh.grid_columnconfigure(0, weight=1)
        label(uh, "Próximos agendamentos", 22, C.TEXT, "bold", display=True, height=28).grid(row=0, column=0, sticky="w")
        button(uh, "Ver agenda completa", lambda: self.app.navigate("agenda"), "link",
               icon="arrow_right", size=12, height=28).grid(row=0, column=1)
        self.upcoming = AppointmentsTable(up, self.repo.today, mode="compact", page_size=5,
                                          empty_text="Nenhum agendamento futuro.")
        self.upcoming.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 16))

    # ------------------------------------------------------------- atualização
    def refresh(self) -> None:
        repo = self.repo
        today = repo.today()
        self.header.set_right_text(date_long_pt(today).capitalize())
        self.header.set_subtitle("Visão geral da operação de hoje." +
                                 ("  ·  Dados de demonstração" if repo.is_demo else ""))
        self._refresh_stats()
        self._refresh_operations()
        self.upcoming.set_rows(repo.upcoming(5))

    def _refresh_stats(self) -> None:
        s = self.repo.dashboard_stats()
        if s["revenue_yesterday"] > 0:
            pct = (s["revenue_today"] - s["revenue_yesterday"]) * 100 / s["revenue_yesterday"]
            delta, kind = f"{pct:+.0f}% vs. ontem", ("positive" if pct >= 0 else "negative")
        else:
            delta, kind = "Sem base de comparação", "neutral"
        self.stats.update_stats([
            StatData("Agendamentos de hoje", str(s["total_today"]),
                     f"{s['done_today']} concluído(s) · {s['remaining_today']} restante(s)"),
            StatData("Serviços em andamento", str(s["in_progress"]),
                     f"Capacidade: {s['capacity']} simultâneo(s)",
                     "Capacidade cheia" if s["in_progress"] >= s["capacity"] else "", "warning"),
            StatData("Veículos prontos", str(s["ready_today"]), "Concluídos hoje",
                     f"{brl(s['receivable_today'])} a receber" if s["receivable_today"] else "", "warning"),
            StatData("Faturamento do dia", brl(s["revenue_today"]), "Valor efetivamente recebido hoje",
                     delta, kind),
        ])

    def _refresh_operations(self) -> None:
        views = self.repo.operations_now()
        self.map.set_active({v.appt.region for v in views})
        shown = [v for v in views if not self.selected_region or v.appt.region == self.selected_region]
        for w in self.ops_list.winfo_children():
            w.destroy()
        total = len(views)
        self.ops_count.configure(text=f"{total} em andamento" if total else "")
        if self.selected_region:
            self.clear_btn.grid(row=0, column=2)
        else:
            self.clear_btn.grid_remove()
        if not shown:
            msg = ("Nenhum serviço em andamento na região selecionada." if self.selected_region
                   else "Nenhum veículo em serviço agora. Inicie um agendamento pela Agenda.")
            label(self.ops_list, msg, 13, C.TEXT_MUTED, anchor="center", height=60).grid(
                row=0, column=0, sticky="ew", pady=30)
        for i, v in enumerate(shown[:MAX_OPERATION_ITEMS]):
            ServiceItem(self.ops_list, v, self.app.appt_actions.advance, self.app.appt_actions.finish,
                        self._select_region, highlighted=bool(self.selected_region)
                        ).grid(row=i, column=0, sticky="ew", pady=(0, 8))
        if len(shown) > MAX_OPERATION_ITEMS:
            label(self.ops_list, f"+ {len(shown) - MAX_OPERATION_ITEMS} serviço(s) em andamento — veja na Agenda.",
                  12, C.TEXT_SECONDARY, height=20).grid(row=MAX_OPERATION_ITEMS, column=0, sticky="w")
        self._update_caption(None)

    # ------------------------------------------------------------------- mapa
    def _select_region(self, region) -> None:
        self.map.select(region)
        self._on_map_select(region)

    def _on_map_select(self, region) -> None:
        self.selected_region = region
        self._refresh_operations()

    def _on_map_hover(self, region) -> None:
        self._update_caption(region)

    def _update_caption(self, hover) -> None:
        region = hover or self.selected_region
        if not region:
            self.map_caption.configure(text="Veículo inteiro")
            self.map_hint.configure(text="Passe o mouse ou clique em uma região para filtrar os serviços.")
            return
        count = sum(1 for v in self.repo.operations_now() if v.appt.region == region)
        self.map_caption.configure(text=region_label(region))
        self.map_hint.configure(text=f"{count} serviço(s) em andamento nesta região.")
