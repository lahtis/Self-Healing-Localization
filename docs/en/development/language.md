config.conf
> language = fi
> base_lang = en
          ↓
LocalizationEngine
> self.lang_code = fi
> self.base_lang = en
          ↓
Localizer
> active file = locales/fi.json
> source file = locales/en.json
          ↓
ui_text(..., default_value="Save")
          ↓
GLFM/local fallback
          ↓
if text in missing and machine trannslation is on.
          ↓
translate_text(
    source_lang="en",
    target_lang="fi",
)
