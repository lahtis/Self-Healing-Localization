"""SHL's own preload hook.

Rekisteröityy mihin tahansa sovellukseen, joka lukee
`shl.preloaders`-entry point -ryhmää. Saa `manager`-olion
parametrina eikä importtaa sovellusta.
"""


def preload(manager):
    """Register SHL's features into the preloader manager."""
    print("[shl] preloading")
    manager.register("shl.translate", translate_text)
    manager.register("shl.engine", LocalizationEngine)
