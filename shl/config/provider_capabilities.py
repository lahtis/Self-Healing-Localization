"""
File: /ui/provider_settings.py
Author: Tuomas Lähteenmäki
License: MIT
Description:
    Main provider settings for SHL.

    This file defines:
        - PROVIDER_CAPABILITIES
        - SHL_WHITELIST
        - PROVIDER_ALLOW
        - PROVIDER_DENY

    PROVIDER_CAPABILITIES describes what the translation provider
    technically supports.

    SHL_WHITELIST describes capabilities that SHL can handle itself
    when the provider does not support them.

    PROVIDER_ALLOW defines the default allowed provider capabilities.

    PROVIDER_DENY defines the default denied provider capabilities.

    These settings are used as the base configuration when creating
    or initializing shl-policy-config.json.
"""


# ---------------------------------------------------------------------------
# Provider technical capabilities
# ---------------------------------------------------------------------------
#
# True  = provider supports the capability
# False = provider does not support the capability
# None  = capability is currently unknown / not verified
#
# These values describe the provider itself, not SHL policy.

PROVIDER_CAPABILITIES = {
    "DeepL": {
        "html": True,
        "glossary": True,
        "formality": True,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": True,
        "website_translation": False,
        "batch_translation": True,
    },

    "Papago": {
        "html": False,
        "glossary": True,
        "formality": True,
        "contextual_suggestions": False,
        "honorific": True,
        "language_detection": True,
        "document_translation": True,
        "website_translation": True,
        "batch_translation": False,
    },

    "Google": {
        "html": True,
        "glossary": False,
        "formality": True,
        "contextual_suggestions": True,
        "honorific": False,
        "language_detection": True,
        "document_translation": True,
        "website_translation": False,
        "batch_translation": True,
    },

    "LibreTranslate": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": True,
        "document_translation": True,
        "website_translation": False,
        "batch_translation": True,
    },

    "MyMemory": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": True,
        "document_translation": True,
        "website_translation": False,
        "batch_translation": True,
    },

    "MicrosoftTranslator": {
        "html": True,
        "glossary": True,
        "formality": True,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": True,
        "document_translation": True,
        "website_translation": False,
        "batch_translation": True,
    },

    "Yandex": {
        "html": None,
        "glossary": True,
        "formality": None,
        "contextual_suggestions": None,
        "honorific": None,
        "language_detection": None,
        "document_translation": None,
        "website_translation": None,
        "batch_translation": None,
    },

    "Local": {},
}


# ---------------------------------------------------------------------------
# SHL internal capability whitelist
# ---------------------------------------------------------------------------
#
# True  = SHL can handle the capability itself when the provider cannot
# False = SHL does not need to handle the capability itself
#
# HTML is the important example:
#
#   Provider supports HTML -> False
#   Provider does not support HTML -> True
#
# Therefore MyMemory and Papago use SHL's HTML handling.

SHL_WHITELIST = {
    "DeepL": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Papago": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Google": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "LibreTranslate": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "MyMemory": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "MicrosoftTranslator": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Yandex": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Local": {},
}


# ---------------------------------------------------------------------------
# Default provider allow settings
# ---------------------------------------------------------------------------
#
# These are the default provider-level permissions used when the policy
# configuration is initially created.
#
# A capability can be enabled here without implying that SHL itself must
# process it. SHL_WHITELIST controls SHL-side fallback handling separately.

PROVIDER_ALLOW = {
    "DeepL": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Papago": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Google": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "LibreTranslate": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "MyMemory": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "MicrosoftTranslator": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Yandex": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Local": {},
}


# ---------------------------------------------------------------------------
# Default provider deny settings
# ---------------------------------------------------------------------------
#
# These are the default denied capabilities.
#
# They are independent from SHL_WHITELIST:
#
# PROVIDER_DENY = provider policy
# SHL_WHITELIST  = SHL internal fallback handling

PROVIDER_DENY = {
    "DeepL": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": True,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Papago": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": False,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Google": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": True,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "LibreTranslate": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": True,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "MyMemory": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": True,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "MicrosoftTranslator": {
        "html": False,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": True,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Yandex": {
        "html": True,
        "glossary": False,
        "formality": False,
        "contextual_suggestions": False,
        "honorific": True,
        "language_detection": False,
        "document_translation": False,
        "website_translation": False,
        "batch_translation": False,
    },

    "Local": {
        "honorific": True,
    },
}
