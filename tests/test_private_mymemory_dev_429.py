from shl.engine.translation.memory.private_mymemory import (
    MyMemoryRateLimitError,
    PrivateMyMemoryBackend,
)

backend = PrivateMyMemoryBackend()

# Simuloi 429-vastaus
try:
    backend._raise_http_error(
        status_code=429,
        response_body=b'{"error": "rate_limited", "message": "Too many requests, retry after 60s"}',
    )
except MyMemoryRateLimitError as e:
    print(f"OK: {type(e).__name__}: {e}")
    # Odotettu: "MyMemoryRateLimitError: Too many requests, retry after 60s"
