## `doc/development/structure.md`


## Project Structure
The library follows a modular design to keep the core logic separate from your application code:


```text
self-healing-localization/
│
├── shl/
│   ├── engine/
│   │   ├── core.py                          # Main localization engine
│   │   ├── localizer.py                     # UI localization
│   │   ├── template_localizer.py            # Template localization
│   │   └── translation/
│   │       ├── __init__.py                  # Translation package exports
│   │       ├── exceptions.py                # Translation exceptions
│   │       ├── cache.py                     # Translation cache
│   │       ├── metadata.py                  # Translation metadata models
│   │       ├── router.py                    # Provider routing
│   │       └── providers/
│   │           ├── mymemory.py              # MyMemory provider
│   │           ├── libretranslate.py        # LibreTranslate provider
│   │           └── libretranslate_mirrors.py # LibreTranslate mirror handling
│   │
│   ├── data/
│   │   ├── languages_top20.json.gz          # Compressed language data
│   │   └── languages/
│   │       ├── mymemory_fallback.json       # MyMemory fallback languages
│   │       └── libretranslate_fallback.json # LibreTranslate fallback languages
│   │
│   ├── utils/
│   │   └── lang_utils.py                    # Language utilities
│   │
│   ├── language_validator.py                # Language validation
│   ├── logging_config.py                    # Logging configuration
│   └── __init__.py                          # Package exports
│
├── tests/
│   ├── test_localizer.py
│   ├── test_template_localizer.py
│   ├── test_core.py
│   ├── test_ai_translation.py
│   ├── test_language_validator.py
│   ├── test_lang_utils.py
│   └── conftest.py
│
├── pyproject.toml
└── README.md
```

Note: Language files (`locales/xx.json`), prompt templates (`prompts/xx.json`) are created in your application, not inside the library.
