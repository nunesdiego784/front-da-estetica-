"""Fontes do Lustre Detail com estratégia de fallback.

Inter -> textos | Barlow Condensed -> títulos e números.

Ordem de resolução:
1. Arquivos .ttf em ``assets/fonts/`` são registrados no Windows (uso privado
   do processo, sem instalar nada no sistema).
2. Se a família preferida existir, ela é usada.
3. Caso contrário, usa-se um fallback comum do Windows
   (Segoe UI / Bahnschrift SemiCondensed / Arial Narrow).
"""
import ctypes
import sys
import tkinter.font as tkfont
from pathlib import Path

import customtkinter as ctk

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

TEXT_CANDIDATES = ["Inter", "Segoe UI", "Helvetica Neue", "Helvetica", "Arial"]
DISPLAY_CANDIDATES = ["Barlow Condensed", "Bahnschrift SemiCondensed",
                      "Bahnschrift", "Arial Narrow", "Segoe UI", "Arial"]

_resolved = {"text": "Segoe UI", "display": "Segoe UI"}
_cache: dict = {}
_registered: list = []


def register_bundled_fonts() -> int:
    """Registra os .ttf de ``assets/fonts`` para este processo (somente Windows).

    Deve ser chamado antes de criar a janela. Devolve quantos arquivos foram
    registrados. Em outros sistemas não faz nada.
    """
    if sys.platform != "win32" or not FONTS_DIR.exists():
        return 0
    FR_PRIVATE = 0x10
    count = 0
    for path in sorted(FONTS_DIR.glob("*.ttf")) + sorted(FONTS_DIR.glob("*.otf")):
        try:
            added = ctypes.windll.gdi32.AddFontResourceExW(str(path), FR_PRIVATE, 0)
            if added:
                count += 1
                _registered.append(path.name)
        except Exception:
            pass
    return count


def init_fonts(root) -> dict:
    """Escolhe as famílias disponíveis (precisa de uma janela Tk já criada)."""
    try:
        families = {f.lower(): f for f in tkfont.families(root)}
    except Exception:
        families = {}
    for role, candidates in (("text", TEXT_CANDIDATES), ("display", DISPLAY_CANDIDATES)):
        for name in candidates:
            if name.lower() in families:
                _resolved[role] = families[name.lower()]
                break
        else:
            _resolved[role] = candidates[1] if len(candidates) > 1 else candidates[0]
    _cache.clear()
    return dict(_resolved)


def fonts_report() -> dict:
    """Famílias efetivamente em uso (útil para o diálogo 'Sobre')."""
    return {"texto": _resolved["text"], "titulos": _resolved["display"],
            "arquivos": list(_registered)}


def text_font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    """Fonte de texto (Inter ou fallback)."""
    key = ("text", size, weight)
    if key not in _cache:
        _cache[key] = ctk.CTkFont(family=_resolved["text"], size=size, weight=weight)
    return _cache[key]


def display_font(size: int = 28, weight: str = "bold") -> ctk.CTkFont:
    """Fonte de títulos e números (Barlow Condensed ou fallback)."""
    key = ("display", size, weight)
    if key not in _cache:
        _cache[key] = ctk.CTkFont(family=_resolved["display"], size=size, weight=weight)
    return _cache[key]
