from datetime import datetime, timezone

from shl.engine.translation.memory.private_mymemory import (
    PrivateMyMemoryBackend,
)


def test_private_mymemory_add_memory():
    memory = PrivateMyMemoryBackend(
        space_uuid="T5x1ovmY6m",
    )

    timestamp = datetime.now(timezone.utc).isoformat()

    result = memory.add_memory(
        content=(
            "Source language: en\n"
            "Target language: fi\n"
            f"Source: SHL private memory test {timestamp}\n"
            "Translation: SHL:n yksityisen muistin testi"
        ),
        memory_type="note",
    )

    assert result is not None
