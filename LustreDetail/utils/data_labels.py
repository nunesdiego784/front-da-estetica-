"""Rótulos em português para valores de domínio (regiões, status, etc.)."""
from data.models import REGIONS


def region_label(key: str) -> str:
    """'capo' -> 'Capô'; vazio -> 'Veículo inteiro'."""
    return REGIONS.get(key, "Veículo inteiro") if key else "Veículo inteiro"


def region_options() -> list:
    """Opções para listas de seleção: [(valor, rótulo)]."""
    return [("", "Veículo inteiro")] + list(REGIONS.items())
