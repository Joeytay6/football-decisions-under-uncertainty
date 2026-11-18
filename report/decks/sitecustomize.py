# Deck mode: shrink every figure so the same point sizes read larger on a 16:9 slide.
import os
_scale = float(os.environ.get("FIG_SCALE", "1"))
if _scale != 1:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.figure as _mf
    _orig = _mf.Figure.__init__
    def _init(self, figsize=None, *a, **k):
        if figsize is not None:
            figsize = (figsize[0] * _scale, figsize[1] * _scale)
        _orig(self, figsize, *a, **k)
    _mf.Figure.__init__ = _init
