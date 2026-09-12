from shl.engine.translation.memory.private_mymemory import PrivateMyMemory


memory = PrivateMyMemory()

result = memory.store(
    source_text="SHL private memory test",
    translated_text="SHL:n yksityisen muistin testi",
    source_lang="en",
    target_lang="fi",
    private=True,
    public=False,
)

print(result)
