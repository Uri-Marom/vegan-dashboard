"""Run once: downloads company logos into static/ for Streamlit to serve."""
import urllib.request
from pathlib import Path

LOGOS = {
    "teva":        "https://logo.clearbit.com/tevapharm.com",
    "amazon":      "https://logo.clearbit.com/amazon.com",
    "eli-lilly":   "https://logo.clearbit.com/lilly.com",
    "abbvie":      "https://logo.clearbit.com/abbvie.com",
    "walmart":     "https://logo.clearbit.com/walmart.com",
    "home-depot":  "https://logo.clearbit.com/homedepot.com",
    "alibaba":     "https://logo.clearbit.com/alibaba.com",
    "berkshire":   "https://logo.clearbit.com/berkshirehathaway.com",
    "honeywell":   "https://logo.clearbit.com/honeywell.com",
}

out = Path(__file__).parent / "static"
out.mkdir(exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0"}
for name, url in LOGOS.items():
    dest = out / f"{name}.png"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        dest.write_bytes(data)
        print(f"  OK  {name}.png ({len(data):,} bytes)")
    except Exception as e:
        print(f"  FAIL {name}: {e}")

print("\nDone. Now: git add static/ && git commit -m 'Add company logos' && git push")
