"""Ícones minimalistas desenhados com Pillow (sem arquivos externos).

Cada ícone é desenhado em uma grade 24x24 com super-amostragem e depois
reduzido, o que dá traços nítidos. Para usar: ``get_icon("search", 18)``.
"""
import math

import customtkinter as ctk
from PIL import Image, ImageDraw

from . import colors as C

_SS = 8        # super-amostragem do desenho
_cache: dict = {}


def _line(d, pts, k, w, color):
    """Polilinha com pontas arredondadas."""
    p = [(x * k, y * k) for x, y in pts]
    d.line(p, fill=color, width=max(1, int(w * k)), joint="curve")
    r = w * k / 2
    for x, y in (p[0], p[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)


def _circle(d, box, k, w, color, fill=None):
    x0, y0, x1, y1 = [v * k for v in box]
    d.ellipse((x0, y0, x1, y1), outline=color, fill=fill, width=max(1, int(w * k)))


def _search(d, k, w, c):
    _circle(d, (4, 4, 16, 16), k, w, c)
    _line(d, [(14.3, 14.3), (20, 20)], k, w, c)


def _bell(d, k, w, c):
    _line(d, [(6, 17), (6, 11), (7.5, 7.5), (10.5, 5.7), (13.5, 5.7),
              (16.5, 7.5), (18, 11), (18, 17), (6, 17)], k, w, c)
    _line(d, [(4.5, 17), (19.5, 17)], k, w, c)
    _line(d, [(10, 20), (14, 20)], k, w, c)
    _line(d, [(12, 3.5), (12, 5.7)], k, w, c)


def _plus(d, k, w, c):
    _line(d, [(12, 5), (12, 19)], k, w, c)
    _line(d, [(5, 12), (19, 12)], k, w, c)


def _eye(d, k, w, c):
    xs = [2 + 20 * i / 24 for i in range(25)]
    top = [(x, 12 - 6 * math.sqrt(max(0, 1 - ((x - 12) / 10) ** 2))) for x in xs]
    bottom = [(x, 12 + 6 * math.sqrt(max(0, 1 - ((x - 12) / 10) ** 2))) for x in reversed(xs)]
    _line(d, top + bottom + [top[0]], k, w, c)
    _circle(d, (9, 9, 15, 15), k, w, c)


def _edit(d, k, w, c):
    _line(d, [(5, 19), (5.8, 15.2), (16, 5), (19, 8), (8.8, 18.2), (5, 19)], k, w, c)
    _line(d, [(14, 7), (17, 10)], k, w, c)


def _x(d, k, w, c):
    _line(d, [(6, 6), (18, 18)], k, w, c)
    _line(d, [(18, 6), (6, 18)], k, w, c)


def _trash(d, k, w, c):
    _line(d, [(5, 7), (19, 7)], k, w, c)
    _line(d, [(9, 7), (9, 4.5), (15, 4.5), (15, 7)], k, w, c)
    _line(d, [(7, 7), (8, 19.5), (16, 19.5), (17, 7)], k, w, c)


def _check(d, k, w, c):
    _line(d, [(5, 12.5), (10, 17.5), (19, 7)], k, w, c)


def _play(d, k, w, c):
    _line(d, [(8, 5.5), (18, 12), (8, 18.5), (8, 5.5)], k, w, c)


def _arrow_right(d, k, w, c):
    _line(d, [(5, 12), (19, 12)], k, w, c)
    _line(d, [(13, 6), (19, 12), (13, 18)], k, w, c)


def _arrow_up(d, k, w, c):
    _line(d, [(12, 19), (12, 5)], k, w, c)
    _line(d, [(6, 11), (12, 5), (18, 11)], k, w, c)


def _arrow_down(d, k, w, c):
    _line(d, [(12, 5), (12, 19)], k, w, c)
    _line(d, [(6, 13), (12, 19), (18, 13)], k, w, c)


def _chevron_left(d, k, w, c):
    _line(d, [(15, 6), (9, 12), (15, 18)], k, w, c)


def _chevron_right(d, k, w, c):
    _line(d, [(9, 6), (15, 12), (9, 18)], k, w, c)


def _chevron_down(d, k, w, c):
    _line(d, [(6, 9), (12, 15), (18, 9)], k, w, c)


def _dots(d, k, w, c):
    for cx in (6, 12, 18):
        r = 1.7 * k
        d.ellipse((cx * k - r, 12 * k - r, cx * k + r, 12 * k + r), fill=c)


def _clock(d, k, w, c):
    _circle(d, (4, 4, 20, 20), k, w, c)
    _line(d, [(12, 8), (12, 12.5), (15.5, 14)], k, w, c)


def _coin(d, k, w, c):
    _circle(d, (4, 4, 20, 20), k, w, c)
    _line(d, [(9, 9.5), (15, 9.5)], k, w, c)
    _line(d, [(9, 14.5), (15, 14.5)], k, w, c)


def _power(d, k, w, c):
    d.arc((5 * k, 5 * k, 19 * k, 19 * k), start=-60, end=240, fill=c, width=max(1, int(w * k)))
    _line(d, [(12, 3.5), (12, 12)], k, w, c)


_DRAWERS = {
    "search": _search, "bell": _bell, "plus": _plus, "eye": _eye, "edit": _edit,
    "x": _x, "trash": _trash, "check": _check, "play": _play,
    "arrow_right": _arrow_right, "arrow_up": _arrow_up, "arrow_down": _arrow_down,
    "chevron_left": _chevron_left, "chevron_right": _chevron_right,
    "chevron_down": _chevron_down, "dots": _dots, "clock": _clock,
    "coin": _coin, "power": _power,
}


def icon_names() -> list:
    """Nomes de ícones disponíveis."""
    return sorted(_DRAWERS)


def render_icon(name: str, size: int = 18, color: str = C.TEXT_SECONDARY,
                weight: float = 1.8) -> Image.Image:
    """Desenha o ícone e devolve uma imagem RGBA com 2x o tamanho lógico (HiDPI)."""
    if name not in _DRAWERS:
        raise KeyError(f"Ícone desconhecido: {name}")
    big = size * 2 * _SS
    k = big / 24.0
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _DRAWERS[name](d, k, weight, color)
    return img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)


def get_icon(name: str, size: int = 18, color: str = C.TEXT_SECONDARY) -> ctk.CTkImage:
    """Devolve um ``CTkImage`` (com cache) do ícone pedido."""
    key = (name, size, color)
    if key not in _cache:
        img = render_icon(name, size, color)
        _cache[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return _cache[key]
