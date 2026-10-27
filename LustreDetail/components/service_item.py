"""Item de 'Operação agora': serviço em andamento com progresso e ações."""
from typing import Callable

import customtkinter as ctk

from utils import colors as C
from utils.data_labels import region_label

from .plate_tag import PlateTag
from .status_badge import StatusBadge
from .widgets import button, label


class ServiceItem(ctk.CTkFrame):
    """Mostra serviço, veículo, placa, início, região, progresso e status.

    Callbacks (recebem o id do agendamento): ``on_advance`` (+25%) e ``on_finish``.
    ``on_region`` recebe a chave da região para destacá-la no mapa do veículo.
    """

    def __init__(self, master, view, on_advance: Callable, on_finish: Callable,
                 on_region: Callable, highlighted: bool = False):
        super().__init__(master, fg_color=C.BG, border_width=1,
                         border_color=C.ACCENT if highlighted else C.BORDER, corner_radius=6)
        a = view.appt
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 0))
        top.grid_columnconfigure(0, weight=1)
        label(top, view.service_name, 15, C.TEXT, "bold", height=22).grid(row=0, column=0, sticky="w")
        StatusBadge(top, a.status).grid(row=0, column=1, sticky="e")

        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.grid(row=1, column=0, sticky="w", padx=14, pady=(4, 0))
        label(mid, view.vehicle_label, 13, C.TEXT_SECONDARY, height=22).grid(row=0, column=0)
        PlateTag(mid, view.plate).grid(row=0, column=1, padx=(8, 0))
        label(mid, f"·  início {a.started_at or a.time}", 12, C.TEXT_MUTED, height=22
              ).grid(row=0, column=2, padx=(10, 0))
        region_text = region_label(a.region) if a.region else "Veículo inteiro"
        if a.region:
            button(mid, f"{region_text}  ›", lambda r=a.region: on_region(r), "link",
                   size=12, height=24, width=int(len(region_text) * 7 + 36)).grid(row=0, column=3, padx=(8, 0))
        else:
            label(mid, f"·  {region_text}", 12, C.TEXT_MUTED, height=22).grid(row=0, column=3, padx=(10, 0))

        bar_row = ctk.CTkFrame(self, fg_color="transparent")
        bar_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(8, 12))
        bar_row.grid_columnconfigure(0, weight=1)
        bar = ctk.CTkProgressBar(bar_row, height=6, corner_radius=3, fg_color=C.BORDER,
                                 progress_color=C.ACCENT)
        bar.set(max(0, min(100, a.progress)) / 100)
        bar.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        label(bar_row, f"{a.progress}%", 18, C.TEXT, "bold", display=True, anchor="e",
              height=22, width=44).grid(row=0, column=1)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=3, padx=(0, 14), sticky="e")
        adv = button(actions, "+25%", lambda: on_advance(a.id), "ghost", size=12, height=30, width=64)
        adv.pack(pady=(0, 6))
        if a.progress >= 100:
            adv.configure(state="disabled")
        button(actions, "Concluir", lambda: on_finish(a.id), "primary", icon="check",
               size=12, height=30, width=96).pack()
