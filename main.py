import shl

# Alustaa lokituksen ja luo error.log-tiedoston tarvittaessa
shl.setup_logging()

from shl.engine import LocalizationEngine

config = {
    "m_translation_enabled": True,
    "m_translation_locale_fallback": True,
    "m_translation_save_original": True,
    "m_translation_provider_priority": ["mymemory"],
    "m_translation_provider_blacklist": ["libretranslate"]
}

engine = LocalizationEngine(lang_code="es", base_lang="en", config=config)

text = engine.ui_text("new_key1", "Hello world.")
text = engine.ui_text("new_key2", "Good morning.")
text = engine.ui_text("new_key3", "Hey girl! Let's go to the park.")
text = engine.ui_text("new_key4", "Hey man, don't shout! Calm down.")
text = engine.ui_text("new_key5", "Hey don't do anything, I'm not ready!")
text = engine.ui_text("new_key6", "Hey do something! This is a false state.")



