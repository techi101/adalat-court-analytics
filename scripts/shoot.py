"""Screenshot pages with Playwright.
python scripts/shoot.py OUT_DIR WIDTH URL [URL...]  -> OUT_DIR/<n>_<width>.png (first viewport)
Also prints horizontal overflow, console errors and failed requests per URL."""
import pathlib, sys
from playwright.sync_api import sync_playwright

out, width, urls = pathlib.Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3:]
full = width < 0
width = abs(width)
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--mute-audio"])
    for i, u in enumerate(urls):
        ctx = b.new_context(viewport={"width": width, "height": 900 if width > 600 else 844},
                            device_scale_factor=1)
        pg = ctx.new_page()
        errs, fails = [], []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("requestfailed", lambda r: fails.append(r.url))
        pg.on("response", lambda r: fails.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        try:
            pg.goto(u, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print("load issue", u, e)
        pg.wait_for_timeout(2500)
        info = pg.evaluate("""async () => { await document.fonts.ready;
          return {ow: document.documentElement.scrollWidth - innerWidth,
                  fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight),
                  h: document.documentElement.scrollHeight,
                  text: document.body.innerText.slice(0, 160).replace(/\\s+/g, ' ')} }""")
        name = out / f"{i}_{width}{'_full' if full else ''}.png"
        pg.screenshot(path=str(name), full_page=full)
        print(name, "| overflow", info["ow"], "| height", info["h"], "| fonts", sorted(set(info["fonts"]))[:8])
        print("   text:", info["text"])
        print("   console errors:", errs[:5], "| failed:", fails[:5])
        ctx.close()
    b.close()
