"""Tema centralizado: espaçamentos, raios, estilos de status e utilidades de escala."""
import customtkinter as ctk

from . import colors as C

# Espaçamentos (unidades lógicas do CustomTkinter)
SP_XS, SP_SM, SP_MD, SP_LG, SP_XL = 4, 8, 12, 16, 24
PAGE_PAD_X = 32
RADIUS = 8          # painéis
RADIUS_SM = 6       # botões e campos
NAV_HEIGHT = 64

# chave -> (texto, cor do texto, cor de fundo do selo)
STATUS_STYLES = {
    "scheduled": ("Agendado", C.TEXT, C.BORDER),
    "in_progress": ("● Em andamento", C.ACCENT, C.tint(C.ACCENT, 0.16)),
    "done": ("Concluído", C.SUCCESS, C.tint(C.SUCCESS, 0.16)),
    "cancelled": ("Cancelado", C.DANGER, C.tint(C.DANGER, 0.16)),
    "pending": ("Pendente", C.ACCENT, C.tint(C.ACCENT, 0.10)),
    "paid": ("Pago", C.SUCCESS, C.tint(C.SUCCESS, 0.16)),
    "active": ("Ativo", C.SUCCESS, C.tint(C.SUCCESS, 0.16)),
    "inactive": ("Inativo", C.TEXT_SECONDARY, C.BORDER),
    "low": ("Estoque baixo", C.DANGER, C.tint(C.DANGER, 0.16)),
    "ok": ("Normal", C.SUCCESS, C.tint(C.SUCCESS, 0.16)),
    "income": ("Receita", C.SUCCESS, C.tint(C.SUCCESS, 0.16)),
    "expense": ("Despesa", C.DANGER, C.tint(C.DANGER, 0.16)),
    "in": ("Entrada", C.SUCCESS, C.tint(C.SUCCESS, 0.16)),
    "out": ("Saída", C.ACCENT, C.tint(C.ACCENT, 0.12)),
}


def apply_theme() -> None:
    """Configura o modo de aparência global (sempre escuro)."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")  # as cores reais são sempre explícitas


def scaling(widget) -> float:
    """Fator de escala (DPI) do widget; 1.0 quando não for possível descobrir."""
    try:
        return float(widget._get_widget_scaling())
    except Exception:
        try:
            return float(widget.winfo_fpixels("1i")) / 96.0
        except Exception:
            return 1.0
