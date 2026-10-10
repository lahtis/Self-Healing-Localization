import logging
logging.basicConfig(level=logging.WARNING)

from shl.engine.translation.providers.deepl import DeepLAdapter
from shl.engine.translation.metadata import TranslationRequest

adapter = DeepLAdapter()  # Free-avain
req = TranslationRequest(
    text="Hello",
    source_lang="en",
    target_lang="fi",
    style_id="test-uuid",
)
# Tämä tulostaa varoituksen ja tekee normaalin käännöksen
result = adapter.translate(req)
print(result)
