"""Fetch district-court numbers from NJDG (njdg.ecourts.gov.in/njdg_v3).

NJDG has no public API, so this opens the dashboard in a headless browser and calls
the same ajaxCall() endpoints the dashboard itself uses when you click a tile.
Everything is saved untouched to raw/njdg_<date>.json; build_data.py parses it.

Run:  python scripts/fetch_njdg.py
"""
import datetime as dt
import json
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
AGE_FLAGS = ["0to1", "1to3", "3to5", "5to10", "10to20", "20to30", "above30"]
STAGE_FLAGS = ["app", "com", "evi", "ple"]

CALLS = [("national_pending", "home/newPendDashboard", "ci_cri=1&stage_ready=3&active_tab=pending"),
         ("national_pending_criminal", "home/newPendDashboard", "ci_cri=3&stage_ready=3&active_tab=pending"),
         ("national_pending_civil", "home/newPendDashboard", "ci_cri=2&stage_ready=3&active_tab=pending")]
CALLS += [(f"state_age_{f}", "home/pendingCasesState", f"flag={f}&ci_cri=1") for f in AGE_FLAGS]
CALLS += [(f"state_lastmonth_{f}", "home/fetchStateData", f"flag={f}&ci_cri=1") for f in ("ins", "disp")]
CALLS += [(f"state_stage_{f}", "home/stagewiseState", f"flag={f}&ci_cri=1") for f in STAGE_FLAGS]

JS = """([url, post]) => new Promise((ok, bad) => {
  const t = setTimeout(() => bad('timeout'), 90000);
  ajaxCall({url, postdata: post, loader: false, callback: r => { clearTimeout(t); ok(r); }});
})"""


def main():
    out = {"source": "https://njdg.ecourts.gov.in/njdg_v3/",
           "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "calls": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--mute-audio"])
        page = browser.new_page()
        page.goto(out["source"], wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2000)
        out["homepage_text"] = page.inner_text("body")[:20000]  # headline tiles, kept for reconciliation
        for name, url, post in CALLS:
            res = page.evaluate(JS, [url, post])
            out["calls"][name] = {"endpoint": url, "post": post, "response": res}
            print("ok", name, flush=True)
        # Per-state dashboard (yearly institution vs disposal, stages), same call the state picker makes.
        states = page.evaluate("""() => [...document.querySelectorAll('#state_code option')]
            .filter(o => o.value && o.value.trim()).map(o => [o.value.trim(), o.textContent.trim()])""")
        out["state_codes"] = states
        for code, name in states:
            post = f"ci_cri=1&stage_ready=3&active_tab=pending&state_code={code}"
            res = page.evaluate(JS, ["home/newPendDashboard", post])
            out["calls"][f"state_pending_{code}"] = {"endpoint": "home/newPendDashboard", "post": post,
                                                     "state": name, "response": res}
            print("ok state", code, name, flush=True)
        browser.close()
    day = out["fetched_at_utc"][:10]
    path = ROOT / "raw" / f"njdg_{day}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", path)


if __name__ == "__main__":
    main()
