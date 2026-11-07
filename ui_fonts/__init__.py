"""Anki UI Fonts. Assumes Anki 26.09.4 / Qt 6 on Windows 11."""


def initialize():
    from .controller import install

    return install(__name__)


# Keep configuration/build tooling importable outside Anki.
try:
    import aqt
except ImportError:
    pass
else:
    if aqt.mw is not None:
        initialize()
