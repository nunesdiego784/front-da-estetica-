"""Animações leves e opcionais (transição de cor e debounce)."""
from . import colors as C


def lerp_color(c1: str, c2: str, t: float) -> str:
    """Interpola linearmente entre duas cores hexadecimais."""
    return C.mix(c2, c1, max(0.0, min(1.0, t)))


def animate_color(widget, apply, start: str, end: str, duration: int = 120, steps: int = 6):
    """Transição suave de cor. ``apply(cor)`` aplica a cor ao widget a cada passo.

    O trabalho agendado anterior do mesmo widget é cancelado, evitando que
    hover rápido deixe a cor em estado inconsistente.
    """
    job = getattr(widget, "_anim_job", None)
    if job is not None:
        try:
            widget.after_cancel(job)
        except Exception:
            pass
        widget._anim_job = None
    delay = max(1, duration // steps)

    def step(i=1):
        try:
            apply(lerp_color(start, end, i / steps))
        except Exception:  # widget destruído durante a animação
            return
        if i < steps:
            widget._anim_job = widget.after(delay, step, i + 1)
        else:
            widget._anim_job = None

    step()


class Debouncer:
    """Agrupa chamadas rápidas (ex.: digitação) em uma só, após ``delay`` ms."""

    def __init__(self, widget, delay: int = 220):
        self.widget, self.delay, self._job = widget, delay, None

    def call(self, fn, *args):
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except Exception:
                pass
        self._job = self.widget.after(self.delay, lambda: self._run(fn, *args))

    def _run(self, fn, *args):
        self._job = None
        fn(*args)
