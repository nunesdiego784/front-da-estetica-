"""Paleta oficial do Lustre Detail e funções auxiliares de mistura de cores.

O dourado/âmbar (ACCENT) é a única cor de destaque predominante.
"""

BG = "#0E0F11"              # fundo principal
SURFACE = "#15171A"         # superfícies e painéis
SURFACE_HOVER = "#1B1E22"   # superfície em destaque / hover
BORDER = "#26292E"          # bordas e divisórias
TEXT = "#ECE9E4"            # texto principal
TEXT_SECONDARY = "#8B9098"  # texto secundário
TEXT_MUTED = "#626770"      # texto discreto
ACCENT = "#D9A441"          # destaque principal
ACCENT_HOVER = "#E3B45A"    # destaque em hover
SUCCESS = "#5FA37C"
DANGER = "#D2695B"          # alerta / erro


def hex_to_rgb(color: str) -> tuple:
    """Converte '#RRGGBB' em (r, g, b)."""
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    """Converte (r, g, b) em '#RRGGBB'."""
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(color: str, base: str, alpha: float) -> str:
    """Mistura ``color`` sobre ``base`` com opacidade ``alpha`` (0..1).

    Substitui a transparência, que o CustomTkinter não oferece: devolve
    sempre uma cor sólida.
    """
    c, b = hex_to_rgb(color), hex_to_rgb(base)
    return rgb_to_hex([c[i] * alpha + b[i] * (1 - alpha) for i in range(3)])


def tint(color: str, alpha: float = 0.14, base: str = SURFACE) -> str:
    """Atalho para ``mix``: versão discreta de ``color`` para fundos de selos."""
    return mix(color, base, alpha)
