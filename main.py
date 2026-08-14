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

engine = LocalizationEngine(lang_code="en", base_lang="fi-FI", config=config)

text = engine.ui_text("new_key1", "Hei maailma.")
engine.ui_text("new_key2", "Hyvää huomenta")
text = engine.ui_text("new_key3", "Hei tyttö! Mennään puistoon")
text = engine.ui_text("new_key4", "Hei mies, älä huido! Ota off.")
text = engine.ui_text("new_key5", "Hei älä tee mitään, koska en ole valmis!")
text = engine.ui_text("new_key6", "Hei tee jotain! Tämä on false tila")


