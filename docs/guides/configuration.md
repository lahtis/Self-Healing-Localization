## `doc/guides/configuration.md`

# Configuration

## config.conf

```ini
[SETTINGS]
language = fi                    # Current UI language
base_lang = en                   # Developer-defined base language
m_translation_enabled = false    # Enable AI translation (default: false)
fallback_to_base = true          # Fall back to base language when key is missing
glfm_lite = true                 # Use GLFM Lite (true) or Full (false)
```

If lang_code is not given when creating the engine, SHL reads the language from config.conf. A value in config.conf overrides environment variables.


| Key | Description | Default |
|--------|-------------|-------------|
| language | Active UI language | auto-detect / en|
| base_lang | Developer-defined base language | en | 
| ai_translation_enabled | Enable automatic AI translation | false | 
| fallback_to_base | Fall back to base language when a key is missing | true | 


Both work without API keys. API key support available via .env file.

---

## Environment Variables (.env)
```ini
MYMEMORY_EMAIL=your@email.com
LIBRETRANSLATE_API_KEY=your-api-key
LIBRETRANSLATE_URL=https://libretranslate.com
```
---

## Language Detection Priority
When `lang_code` is not provided to `LocalizationEngine`, the language is resolved in this order:

1. config.conf → [SETTINGS] language
2. SHL_LANGUAGE environment variable
3. LANG environment variable
4. Default: "en"

An explicit `lang_code` argument always takes highest priority and skips auto-detection.

---

