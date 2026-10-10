import os
from urllib.request import Request, urlopen
from urllib.parse import quote

# Lataa .env ensin
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v.strip().strip('"').strip("'")

email = os.getenv("MYMEMORY_EMAIL", "")
print(f"Email: '{email}'")

url = f"https://api.mymemory.translated.net/get?q={quote('Hello')}&langpair=en|fi"
if email:
    url += f"&de={quote(email)}"

print(f"URL: {url[:80]}...")
try:
    req = Request(url, headers={"User-Agent": "SHL-Test/1.0"})
    with urlopen(req, timeout=10) as r:
        data = r.read().decode()
        print(f"Status: OK")
        print(f"Response: {data[:200]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
