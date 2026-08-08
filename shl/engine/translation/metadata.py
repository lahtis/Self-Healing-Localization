"""
Metadata for translation requests.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class TranslationRequest:
    """
    Translation request with metadata.

    Three levels of metadata:
    1. All providers: text, source_lang, target_lang
    2. Some providers: context_type, domain, screen, component, formality, glossary, html_format
    3. SHL internal: key, source_id, metadata
    """

    # Taso 1: Kaikki palvelut
    text: str
    source_lang: str
    target_lang: str

    # Taso 2: Osa palveluista (DeepL, Google, OpenAI)
    context_type: Optional[str] = None      # "button", "label", "menu", "tooltip"
    domain: Optional[str] = None            # "desktop_ui", "web", "mobile"
    formality: Optional[str] = None         # "formal", "informal" (DeepL)
    glossary: Optional[Dict[str, str]] = None  # {"Save": "Tallenna"}
    html_format: bool = False               # LibreTranslate, DeepL, Google

    # Taso 3: SHL:n sisäinen metadata
    key: Optional[str] = None               # "settings.save"
    screen: Optional[str] = None            # "settings", "main", "login"
    component: Optional[str] = None         # "save_button"
    source_id: Optional[str] = None         # "shl://settings/save_button"
    metadata: Dict[str, Any] = field(default_factory=dict)  # Joustava lisätieto


@dataclass
class TranslationResult:
    """Translation result with metadata."""
    translated_text: str
    source: str                              # "mymemory", "libretranslate", "deepl"
    confidence: Optional[float] = None
    raw_response: Optional[Dict[str, Any]] = None
    request_metadata: Optional[TranslationRequest] = None  # Säilytetään metadata
