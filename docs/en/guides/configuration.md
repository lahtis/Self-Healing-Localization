# Configuration

## config.conf

```ini
[SETTINGS]
language = fi                    # Active UI target language
base_lang = en                   # Developer-defined source code language
m_translation_enabled = false    # Enable Machine translation (default: false)
fallback_to_base = true          # Fall back to base language when key is missing
glfm_lite = true                 # Use GLFM Lite (true) or Full (false)
```

If lang_code is not explicitly provided when initializing the engine, SHL automatically reads the configuration from config.conf. Values defined in config.conf take precedence over environment variables.


| Key | Description | Default |
|--------|-------------|-------------|
| language | Active UI language | en (or auto-detected) |
| base_lang | Developer-defined source code language | en | 
| m_translation_enabled | Enable automatic machine translation | false | 
| fallback_to_base | Fall back to base language when a key is missing | true |
| glfm_lite | Use GLFM Lite (true) or Full (false) | true | 

---

## Environment Variables (.env)
```ini
MYMEMORY_EMAIL=your@email.com
LIBRETRANSLATE_API_KEY=your-api-key
LIBRETRANSLATE_URL=https://libretranslate.com
DEEPL_API_KEY=your-api-key
GOOGLE_API_KEY=your-api-key
```

| Variable                 | Description                       | Example           |
| ------------------------ | --------------------------------- | ----------------- |
| `DEEPL_API_KEY`          | DeepL API key                     | `your-deepl-key`  |
| `GOOGLE_API_KEY`         | Google Cloud API key              | `your-google-key` |
| `LIBRETRANSLATE_API_KEY` | LibreTranslate API key (optional) | `your-lt-key`     |

Only API keys are fetched from environment variables:
- Language settings (language, base_lang) are read exclusively from config.conf
- Environment variables are used only for API keys

SHL automatically selects the provider in this order:
- DeepL – if an API key is set
- Google Cloud – if an API key is set
- LibreTranslate – default, does not require a key
- MyMemory – last resort

---

## Language Detection Priority
When lang_code is not provided directly to LocalizationEngine, the target language is resolved using the following priority order:

1. config.conf → [SETTINGS] language
2. SHL_LANGUAGE environment variable
3. LANG environment variable
4. Default fallback: "en"

Note: Providing an explicit lang_code argument during initialization always takes the highest priority and bypasses this detection chain completely.

---

## Translation Services
Both integrated services can be used out of the box without any API keys. Optional API keys and service-specific configurations can be provided via environment variables or a .env file.

| Service | Role | Limits | Notes |
|---------|------|--------|-------|
| **MyMemory** | Primary provider | 1,000 chars/day (30,000 with email) | Translation memory with machine-translation fallback |
| **LibreTranslate** | Fallback provider | Public instances are rate-limited | Open-source machine-translation service |
| **DeepL** | Premium provider (optional) | API key required | Highest quality, supports formality & glossary |
| **Google Cloud Translation** | Premium provider (optional) | API key required | Supports HTML formatting, automatic failover |

---
