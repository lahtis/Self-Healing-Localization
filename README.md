# SHL — Self-Healing Localization

> **Your app speaks English. Your users don't.**
> Add a new menu item. SHL translates it automatically.
> No `xgettext`. No `.po` files. No `msgfmt`. No manual work.

[![PyPI](https://img.shields.io/pypi/v/self-healing-localization)](https://pypi.org/project/self-healing-localization/)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status: Beta](https://img.shields.io/badge/Status-Beta-yellow)
[![Downloads](https://static.pepy.tech/badge/self-healing-localization)](https://pepy.tech/project/self-healing-localization)

<!-- TARKISTA: lisää tähän GIF demosta (Flet-vieraskirja EN → FR).
     Kun GIF on valmis, korvaa tämä kommentti kuvalla:
     ![Demo](docs/demo.gif) -->

---

## The self-healing loop

1. You add `ui_text("Settings", "Settings")` to your code.
2. You start your app.
3. SHL scans your source, finds the new key, translates it, and saves it.
4. Next time the user opens the menu, the translation is already there.

**Missing key → translate → save → ready.**

This is what "self-healing" means: the library notices what's missing
and fixes it — without you having to run a build step, update a `.pot`
file, or wait for a translator.

---


## Why SHL?

Most localization libraries assume you will maintain translation files by hand.
SHL assumes the opposite: **missing translations are a bug, and bugs should fix
themselves.**

## Why SHL?

- **Automatic** — missing keys are created and translated on first use.
- **Self-healing** — add a new string, and the translation is ready on
  the next startup. No manual step.
- **Eager, not lazy** — translations are done at startup, not when the
  user opens a menu. No UI lag.
- **Resilient** — if one provider fails, the next one takes over.
- **Offline-capable** — works without API keys (local translation).
- **Zero-dependency core** — no GUI, no ORM, no framework.
- **gettext-style API, JSON under the hood** — `L("key")` and
  `ui_text(...)` feel familiar, but translations live in plain
  `locales/<lang>.json` files. No `.po` parsing, no `.mo` compilation.
- **Works alongside gettext** — the scanner already recognizes `_()`,
  `gettext()`, and `ngettext()` calls.
- **10 providers** — Local, MyMemory, DeepL, Google, Microsoft,
  LibreTranslate, LibreTranslate Community, Papago, Yandex,
  DetectLanguage.
  
---

## The ecosystem

SHL is more than one library. It is a small ecosystem of optional tools
that share the same core.

| Component | What it does | Needs | Link |
|---|---|---|---|
| **`shl`** | The library itself | Python 3.10+ | [Codeberg](https://codeberg.org/lahtis/Self_Healing_Localization) |
| **`shl-gui`** | GTK4 management GUI for locales and providers | GTK4 (optional) | [Codeberg](https://codeberg.org/lahtis/Self_Healing_Localization) |
| **SHL Policy Editor** (bundled) | Tkinter-based editor for `config.json` | Tkinter (stdlib) | [Codeberg](https://codeberg.org/lahtis/Self_Healing_Localization/src/branch/main/shl_policy_editor) |
| **SHL Policy Editor** (standalone) | Full GTK4 visual editor for provider policy | GTK4 | [Codeberg](https://codeberg.org/lahtis/shl_policy_editor) |
| **Digital Guestbook** | Demo application: a multilingual guestbook for hotels | Flet | [Codeberg](https://codeberg.org/lahtis/Digital-Guestbook) |

You only need `shl`. The rest are optional.
---

## Quick Start

### Installation

```bash
pip install self-healing-localization
```

### Three-line example

```bash
from shl.engine import LocalizationEngine

engine = LocalizationEngine(base_lang="eng", lang_code="fin")
print(engine.ui_text("welcome", "Welcome!"))

# → "Tervetuloa!" (if a translation exists)
```

And locales/fin.json now contains:

{
    "greeting": "Hei!"
}

That's it. The key "greeting" did not exist, so SHL created it,
translated "Hello!" → "Hei!", and saved the result. The next time
the app runs, the translation is read from disk — no network call.

### What just happened?

- 1. LocalizationEngine(lang_code="fin") — user wants Finnish UI.
- 2. ui_text("greeting", "Hello!") — the key "greeting" is not in locales/fin.json.
- 3. SHL asks the provider router for a translation: "Hello!" → "Hei!".
- 4. The result is saved to locales/fin.json with the key "greeting".
- 5. Next run: ui_text("greeting", "Hello!") returns "Hei!" directly from disk — no provider call.

This is the self-healing loop: missing key → translate → save → reuse.


### With machine translation enabled
```python
from shl.engine import LocalizationEngine

config = {"m_translation_enabled": True}
engine = LocalizationEngine(lang_code="fin", config=config)
print(engine.ui_text("greeting", "Hello!"))
```
Output: 

Hei!

That's it. The key "greeting" did not exist in locales/fin.json, so SHL created it, translated "Hello!" → "Hei!", and saved the result. The next time the app runs, the translation is read from disk — no network call.

---

## Limitations

* SHL does not translate user-generated content. If your users write messages, comments, or reviews, those stay in the language they were written in. SHL is a localization library, not a content translation service.
* SHL does not modify user data or configuration files. It only operates on the application's own localization layer.
* Machine translation quality depends on the provider. Review translations before shipping.
* Some providers require paid subscriptions or API keys.
* SHL is in beta. APIs may change before 1.0.

---

## Documentation
- Canonical Repository (Codeberg): https://codeberg.org/lahtis/Self_Healing_Localization
- GitHub Mirror: https://github.com/lahtis/Self-Healing-Localization
- Documentation: https://codeberg.org/lahtis/Self_Healing_Localization/src/branch/main/docs
- Full guide: https://codeberg.org/lahtis/Self_Healing_Localization/src/branch/main/docs/guide.md
- Demo video: https://www.youtube.com/watch?v=t5veRZtt3dU
- SHL Policy Editor: https://codeberg.org/lahtis/shl_policy_editor


---

## Contributing

Contributions are welcome.  
This project aims to become a new standard for open‑source localization — simple, automatic, and self‑maintaining.

---

## License

MIT License — free for personal and commercial use.

---

## Vision

Localization should never be a burden.

With SHL, any project can become multilingual — automatically, reliably, and without manual maintenance.

> **No more missing translations. No more incomplete language packs. Localization that heals itself.**


#localization • #i18n • #l10n • #self-healing • #translation • #multilingual #json • #python • #developer-tools • #automation • #templates • #cli #ai-assisted • #language-files • #internationalization • #localization-engine


