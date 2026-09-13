from shl.engine.translation.memory.private_mymemory import (
    PrivateMyMemoryBackend,
)


memory = PrivateMyMemoryBackend(
    space_uuid="T5x1ovmY6m",
)

result = memory.add_memory(
    content=(
        "Source language: en\n"
        "Target language: fi\n"
        "Source: SHL private memory test\n"
        "Translation: SHL:n yksityisen muistin testi"
    ),
    memory_type="note",
)

print(result)
