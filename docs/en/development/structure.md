## `doc/en/development/structure.md`


## Project Structure to version 0.2.0 to 0.2.2
The library follows a modular design to keep the core logic separate from your application code:


```text
self-healing-localization/
│
├── shl/
│   ├── engine/
│   │   ├── __init__.py               			# Engine package exports
│   │   ├── core.py                           	# Main localization engine
│   │   ├── localizer.py                      	# UI localization
│   │   ├── template_localizer.py             	# Template localization
│   │   └── translation/ 
│   │       ├── __init__.py                   	# Translation package exports
│   │       ├── exceptions.py                 	# Translation exceptions
│   │       ├── cache.py                      	# Translation cache
│   │       ├── metadata.py                   	# Translation metadata models
│   │       ├── router.py                     	# Provider routing
│   │       └── providers/
│   │           ├── __init__.py               	# Providers package exports
│   │           ├── base.py               		# Base provider
│   │           ├── deepl.py               		# DeepL provider
│   │           ├── googlev2.py               	# Google v2 provider
│   │           ├── google_registry.py          # Google registery
│   │           ├── mymemory.py               	# MyMemory provider
│   │           ├── mymemory_registry.py        # MyMemory registry
│   │           ├── libretranslate.py         	# LibreTranslate provider
│   │           ├── libretranslate_mirrors.py 	# LibreTranslate mirror handling
│   │           └── libretranslate_registry.py 	# LibreTranslate registry
│   │
│   ├── data/
│   │   └── languages_top20.json.gz           	# Compressed language data
│   │   
│   │
│   ├── utils/
│   │   ├── __init__.py						  	# Utils package exports
│   │   ├── glfm_load_database.py			  	# GLFM database loader (`shl/data/languages_top20.json.gz`)
│   │   └── lang_utils.py                     	# Language utilities
│   │
│   │
│   ├── language_validator.py                 	# Language validation
│   ├── logging_config.py                     	# Logging configuration
│   ├── __init__.py                           	# Package exports
│   └── _version.py                           	# Version exports
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
