"""Desenho do veículo visto de cima com Pillow (sem Tkinter).

Toda a geometria está em um espaço de projeto de 220x440 unidades. O desenho
é feito em alta resolução (super-amostragem) e reduzido, o que gera bordas
suaves. Cada região da carroceria possui uma máscara usada para:

* pintar destaques (hover, seleção, região com serviço em andamento);
* descobrir qual região está sob o mouse (``hit_test``).
"""
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import colors as C

DESIGN_W, DESIGN_H = 220, 440

REGION_ORDER = ["capo", "teto", "porta_malas", "esquerdo", "direito"]

# retângulos (x0, y0, x1, y1) em unidades de projeto; a máscara final é
# a interseção com a silhueta do carro.
_REGION_RECTS = {
    "capo": (0, 0, 220, 150),
    "porta_malas": (0, 296, 220, 440),
    "esquerdo": (0, 150, 74, 296),
    "direito": (146, 150, 220, 296),
    "teto": (74, 182, 146, 268),
}
_REGION_CENTERS = {
    "capo": (110, 86), "teto": (110, 225), "porta_malas": (110, 357),
    "esquerdo": (55, 223), "direito": (165, 223),
}
_GLASS = [
    [(80, 152), (140, 152), (146, 182), (74, 182)],   # para-brisa
    [(74, 268), (146, 268), (140, 296), (80, 296)],   # vidro traseiro
]
_WHEELS = [(31, 78, 47, 132), (31, 308, 47, 362), (173, 78, 189, 132), (173, 308, 189, 362)]
_WHEEL_COLOR = "#08090A"
_GLASS_COLOR = "#0B0C0E"


def _silhouette_points(n: int = 360):
    """Superelipse (formato de carroceria arredondada) em unidades de projeto."""
    p = 4.2
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        y = 220 + 198 * math.copysign(abs(s) ** (2 / p), s)
        taper = 1 - 0.16 * ((y - 220) / 198) ** 2   # frente e traseira levemente mais estreitas
        x = 110 + 72 * taper * math.copysign(abs(c) ** (2 / p), c)
        pts.append((x, y))
    return pts


class CarRenderer:
    """Renderiza o carro nos estados normal, hover, selecionado e ativo."""

    SS = 3  # fator de super-amostragem

    def __init__(self, out_width: int, bg_color: str = C.SURFACE):
        self.out_w = int(out_width)
        self.out_h = int(round(out_width * DESIGN_H / DESIGN_W))
        self.k = self.out_w / DESIGN_W          # unidades de projeto -> pixels finais
        self.bg = bg_color
        self.body = C.SURFACE_HOVER
        self._hi = self.k * self.SS             # unidades -> pixels em alta resolução
        self._hi_size = (self.out_w * self.SS, self.out_h * self.SS)
        self._sil = _silhouette_points()
        self._masks = {}
        self._edges = {}
        self._cache = {}
        self._build_hit_map()
        self._build_layers()

    # ------------------------------------------------------------ construção
    def _scale(self, pts, factor):
        return [(x * factor, y * factor) for x, y in pts]

    def _rect_mask(self, rect, factor, size):
        m = Image.new("L", size, 0)
        x0, y0, x1, y1 = [v * factor for v in rect]
        ImageDraw.Draw(m).rectangle((x0, y0, x1, y1), fill=255)
        return m

    def _sil_mask(self, factor, size):
        m = Image.new("L", size, 0)
        ImageDraw.Draw(m).polygon(self._scale(self._sil, factor), fill=255)
        return m

    def _build_hit_map(self):
        """Mapa de cliques em resolução final: valor do pixel = índice da região + 1."""
        size = (self.out_w, self.out_h)
        sil = self._sil_mask(self.k, size)
        hit = Image.new("L", size, 0)
        d = ImageDraw.Draw(hit)
        for idx, name in enumerate(REGION_ORDER, start=1):
            x0, y0, x1, y1 = [v * self.k for v in _REGION_RECTS[name]]
            d.rectangle((x0, y0, x1, y1), fill=idx)
        self._hit = ImageChops.multiply(hit, sil)

    def _build_layers(self):
        size = self._hi_size
        hi = self._hi
        # camada base: fundo, rodas, espelhos e silhueta preenchida
        base = Image.new("RGB", size, self.bg)
        d = ImageDraw.Draw(base)
        for x0, y0, x1, y1 in _WHEELS:
            d.rounded_rectangle((x0 * hi, y0 * hi, x1 * hi, y1 * hi), radius=5 * hi, fill=_WHEEL_COLOR)
        for sx in (1, -1):  # espelhos retrovisores
            cx = 110 + sx * 76
            pts = [(cx, 176), (cx + sx * 12, 184), (cx, 190)]
            d.polygon(self._scale(pts, hi), fill=self.body, outline=C.BORDER)
        d.polygon(self._scale(self._sil, hi), fill=self.body)
        self._base = base

        # camada de detalhes (RGBA): contorno, vidros e divisórias entre regiões
        det = Image.new("RGBA", size, (0, 0, 0, 0))
        dd = ImageDraw.Draw(det)
        for glass in _GLASS:
            dd.polygon(self._scale(glass, hi), fill=_GLASS_COLOR, outline=C.BORDER)
        for x in (74, 146):
            dd.line(self._scale([(x, 150), (x, 296)], hi), fill=C.BORDER, width=max(1, int(hi * 1.2)))
        dd.line(self._scale([(74, 182), (146, 182)], hi), fill=C.BORDER, width=max(1, int(hi * 1.2)))
        dd.line(self._scale([(74, 268), (146, 268)], hi), fill=C.BORDER, width=max(1, int(hi * 1.2)))
        dd.polygon(self._scale(self._sil, hi), outline=C.TEXT_MUTED, width=max(1, int(hi * 1.4)))
        self._details = det

        # máscaras (e contornos) de cada região em alta resolução
        sil = self._sil_mask(hi, size)
        edge_w = 2 * self.SS + 1
        for name in REGION_ORDER:
            m = ImageChops.multiply(self._rect_mask(_REGION_RECTS[name], hi, size), sil)
            self._masks[name] = m
            self._edges[name] = ImageChops.subtract(
                m.filter(ImageFilter.MaxFilter(edge_w)), m.filter(ImageFilter.MinFilter(edge_w)))

    # ------------------------------------------------------------------ uso
    def hit_test(self, x: float, y: float):
        """Região sob o ponto (pixels finais) ou ``None``."""
        xi, yi = int(x), int(y)
        if not (0 <= xi < self.out_w and 0 <= yi < self.out_h):
            return None
        idx = self._hit.getpixel((xi, yi))
        return REGION_ORDER[idx - 1] if 1 <= idx <= len(REGION_ORDER) else None

    def region_center(self, name: str):
        """Centro da região em pixels finais."""
        cx, cy = _REGION_CENTERS[name]
        return cx * self.k, cy * self.k

    def render(self, selected=None, hover=None, active=()) -> Image.Image:
        """Imagem RGB final no estado pedido (com cache)."""
        key = (selected, hover, frozenset(active))
        if key in self._cache:
            return self._cache[key]
        img = self._base.copy()
        for name in REGION_ORDER:
            if name == selected:
                fill = C.mix(C.ACCENT, self.body, 0.34)
            elif name == hover:
                fill = C.mix(C.ACCENT, self.body, 0.18)
            elif name in active:
                fill = C.mix(C.ACCENT, self.body, 0.10)
            else:
                continue
            img.paste(fill, mask=self._masks[name])
        img = Image.alpha_composite(img.convert("RGBA"), self._details).convert("RGB")
        if selected in self._edges:
            img.paste(C.ACCENT, mask=self._edges[selected])
        d = ImageDraw.Draw(img)
        for name in active:
            if name in _REGION_CENTERS:
                cx, cy = [v * self._hi for v in _REGION_CENTERS[name]]
                r = 4.5 * self._hi
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=C.ACCENT)
        out = img.resize((self.out_w, self.out_h), Image.Resampling.LANCZOS)
        if len(self._cache) > 48:
            self._cache.clear()
        self._cache[key] = out
        return out
