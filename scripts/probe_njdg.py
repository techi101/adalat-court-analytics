"""Probe NJDG: load the dashboard, log every XHR/fetch request + response size.
Used once to find the JSON endpoints the dashboard itself calls."""
import json, sys
from playwright.sync_api import sync_playwright

log = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--mute-audio"])
    pg = b.new_page()
    def on_resp(r):
        if r.request.resource_type in ("xhr", "fetch"):
            try:
                body = r.text()
            except Exception:
                body = ""
            log.append({"url": r.url, "method": r.request.method,
                        "post": r.request.post_data, "status": r.status,
                        "len": len(body), "head": body[:400]})
    pg.on("response", on_resp)
    pg.goto("https://njdg.ecourts.gov.in/njdg_v3/", wait_until="networkidle", timeout=90000)
    pg.wait_for_timeout(4000)
    json.dump(log, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    b.close()
print(len(log))
