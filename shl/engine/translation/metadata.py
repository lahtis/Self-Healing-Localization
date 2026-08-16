"""
File: metadata.py — metadata for translation requests.
Author: Tuomas Lähteenmäki
Version: 0.2.4
License: MIT
Description: Data transfer objects (DTO) for standardizing localized text payloads,
             context preservation markers, and external provider results.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class TranslationRequest:
    """
    Translation request schema with multi-level metadata execution context.

    Three tiers of attributes:
    1. Core Pipeline: text, source_lang, target_lang (All adapters)
    2. Context Controls: context_type, domain, formality, glossary, html_format (Advanced adapters)
    3. Engine Internal: key, screen, component, source_id, metadata (SHL tracking layer)
    """

    # Tier 1: Core Pipeline (All providers)
    text: str
    source_lang: str
    target_lang: str

    # Tier 2: Context Controls (DeepL, Google Cloud, Papago and LLM-backed routers)
    context_type: Optional[str] = None                  # e.g., "button", "label", "menu", "tooltip"
    domain: Optional[str] = None                        # e.g., "desktop_ui", "web", "mobile"
    formality: Optional[str] = None                     # e.g., "formal", "informal"
    honorific: Optional[bool] = None                    # Papago-specific: True = polite/honorific style
    glossary: Optional[Dict[str, Any]] = None           # e.g., {"Save": "Tallenna"}
    glossary_id: Optional[str] = None                   # DeepL glossary ID
    html_format: bool = False                           # Explicit markup protection handling

    # Tier 3: Engine Internal Tracking
    key: Optional[str] = None                           # e.g., "settings.save"
    screen: Optional[str] = None                        # e.g., "settings", "main", "login"
    component: Optional[str] = None                     # e.g., "save_button"
    source_id: Optional[str] = None                     # e.g., "shl://settings/save_button"
    metadata: Dict[str, Any] = field(default_factory=dict)  # Flexible extension dict

@dataclass
class TranslationResult:
    """Standardized output container enclosing evaluated strings and transaction analytics."""
    translated_text: str
    source: str                             # e.g., "mymemory", "libretranslate", "deepl", "google"
    confidence: Optional[float] = None
    raw_response: Optional[Dict[str, Any]] = None
    request_metadata: Optional[TranslationRequest] = None  # Retained execution footprint
