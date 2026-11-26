"""Call NJDG's own ajaxCall() inside the page (so its CSRF token is used) and dump raw JSON."""
import json, sys
from playwright.sync_api import sync_playwright

CALLS = json.loads(sys.argv[2])  # list of [name, url, postdata]
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--mute-audio"])
    pg = b.new_page()
    pg.goto("https://njdg.ecourts.gov.in/njdg_v3/", wait_until="networkidle", timeout=90000)
    pg.wait_for_timeout(2000)
    for name, url, post in CALLS:
        try:
            res = pg.evaluate("""([url, post]) => new Promise((ok, bad) => {
                const t = setTimeout(() => bad('timeout'), 60000);
                ajaxCall({url, postdata: post, loader: false, callback: r => { clearTimeout(t); ok(r); }});
            })""", [url, post])
        except Exception as e:
            res = {"__error": str(e)}
        out[name] = res
        print(name, "ok" if "__error" not in (res or {}) else res, flush=True)
    b.close()
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
