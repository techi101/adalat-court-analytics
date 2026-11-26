"""Turn the raw NJDG snapshot into site/data.json.

Every number on the page comes from this file. Nothing is typed in by hand except the
three labelled model defaults in MODEL_DEFAULTS (each with its source or 'assumption').

Run:  python scripts/build_data.py raw/njdg_2026-11-26.json
"""
import io
import json
import pathlib
import re
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOCUS = ["Uttar Pradesh", "Maharashtra", "Kerala"]

MODEL_DEFAULTS = {
    "witnesses_before": {"value": 2.5, "source": "adalat.ai homepage quote from a Judicial Magistrate: 'two to three witnesses a day' before Adalat AI (midpoint)"},
    "witnesses_after": {"value": 5.5, "source": "same quote: 'five to six' with real-time transcription (midpoint)"},
    "coverage": {"value": 0.25, "source": "adalat.ai homepage: '20-25% courtroom coverage nationwide' (upper end)"},
    "evidence_share": {"value": 0.5, "source": "ASSUMPTION. Share of a contested trial's court time spent recording evidence. No public source found; slider shows the range."},
    "contested_share": {"value": None, "source": "NJDG homepage: 'Contested: 25% of disposal in last month' (computed below)"},
}


def tilde(s, num=True):
    parts = [p.strip().strip('"').replace("#", " ").strip() for p in str(s).split("~")]
    return [int(p) for p in parts] if num else parts


def table(resp):
    t = pd.read_html(io.StringIO(resp["tbl_str"]))[0]
    t = t[t["State"].astype(str) != "Total:"].copy()
    for c in ("Civil", "Criminal", "Total"):
        t[c] = pd.to_numeric(t[c], errors="coerce").fillna(0).astype(int)
    total_row = pd.read_html(io.StringIO(resp["tbl_str"]))[0].iloc[-1]
    return t.set_index("State"), int(total_row["Total"])


def num(txt):
    return int(txt.replace(",", ""))


def main(raw_path):
    raw = json.loads(pathlib.Path(raw_path).read_text(encoding="utf-8"))
    C = {k: v["response"] for k, v in raw["calls"].items()}
    home = raw["homepage_text"]

    # Headline tiles from the homepage text (what a visitor to NJDG sees).
    def tile(label):
        m = re.search(label + r"\s*\n\s*([\d,]+)", home)
        return num(m.group(1))
    tiles = {"civil": tile("Civil Cases"), "criminal": tile("Criminal Cases"), "total": tile("Total Cases")}
    m = re.search(r"Instituted in last month\s*\n\s*\n?([\d,]+)\s+([\d,]+)\s+([\d,]+)", home)
    inst_lm = [num(x) for x in m.groups()]
    m = re.search(r"Disposal in last month\s*\n\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)", home)
    disp_lm = [num(x) for x in m.groups()]
    m = re.search(r"Contested[\s\S]*?Disposal in last month\s*\n\s*\n?([\d,]+)\s+([\d,]+)\s+([\d,]+)", home)
    contested_lm = [num(x) for x in m.groups()]
    contested_share = contested_lm[2] / disp_lm[2]
    MODEL_DEFAULTS["contested_share"]["value"] = round(contested_share, 3)

    nat = C["national_pending"]
    years = tilde(nat["insyear"])
    flows = [{"year": y, "instituted": i, "disposed": d} for y, i, d in
             zip(years, tilde(nat["ins_count"]), tilde(nat["disp_count"]))]
    flows.sort(key=lambda r: r["year"])

    # Pending cases by year of filing (the backlog curve).
    by_filing = sorted(zip(tilde(nat["year"]), tilde(nat["year_count"])))
    by_filing = [{"year": y, "pending": c} for y, c in by_filing if c > 0]

    # Stage (purpose of next hearing) for all pending cases, criminal and civil.
    def stages(resp, top=10):
        names, counts = tilde(resp["purpose_name"], False), tilde(resp["purpose_count"])
        rows = [{"stage": n or "(no stage recorded)", "pending": c} for n, c in zip(names, counts)]
        rows.sort(key=lambda r: -r["pending"])
        return rows[:top], sum(counts), next((r["pending"] for r in rows if r["stage"] == "(no stage recorded)"), 0)
    stage_all, stage_sum, blank_stage = stages(nat, 12)
    stage_cri, _, _ = stages(C["national_pending_criminal"], 8)

    delay = sorted(zip(tilde(nat["delayName"], False), tilde(nat["delay_count"])), key=lambda r: -r[1])
    delay = [{"reason": n, "pending": c} for n, c in delay]

    age_labels = ["< 1 yr", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10-20 yrs", "20-30 yrs", "30+ yrs"]
    age_nat = dict(zip(age_labels, tilde(nat["agewise_count"])))

    # State tables.
    flags = ["0to1", "1to3", "3to5", "5to10", "10to20", "20to30", "above30"]
    age_tables = {f: table(C[f"state_age_{f}"]) for f in flags}
    ins_t, ins_total = table(C["state_lastmonth_ins"])
    disp_t, disp_total = table(C["state_lastmonth_disp"])
    evi_t, evi_total = table(C["state_stage_evi"])
    stage_group_nat = dict(zip(tilde(nat["purposename"], False), tilde(nat["stagewise_count"])))

    states = []
    for k, v in raw["calls"].items():
        if not k.startswith("state_pending_"):
            continue
        r, name = v["response"], v["state"]
        sf = sorted(zip(tilde(r["insyear"]), tilde(r["ins_count"]), tilde(r["disp_count"])))
        ages = dict(zip(age_labels, tilde(r["agewise_count"])))
        pending = sum(ages.values())
        names, counts = tilde(r["purpose_name"], False), tilde(r["purpose_count"])
        witness = sum(c for n, c in zip(names, counts) if n.lower().startswith("witness"))
        y25 = next(x for x in sf if x[0] == 2025)
        states.append({
            "state": name, "pending": pending,
            "older_than_3y": sum(v for kk, v in ages.items() if kk not in ("< 1 yr", "1-3 yrs")),
            "witness_stage": witness,
            "ins_2025": y25[1], "disp_2025": y25[2],
            "flows": [{"year": y, "instituted": i, "disposed": d} for y, i, d in sf],
            "ages": ages,
        })
    states.sort(key=lambda s: -s["pending"])

    # Reconciliation: places where NJDG's own numbers disagree with each other.
    cri_age = tilde(C["national_pending_criminal"]["agewise_count"])
    civ_age = tilde(C["national_pending_civil"]["agewise_count"])
    checks = [
        {"what": "Criminal cases: headline tile vs sum of its own age buckets",
         "a_label": "Headline tile", "a": tiles["criminal"],
         "b_label": "Sum of age buckets", "b": sum(cri_age)},
        {"what": "Civil cases: headline tile vs sum of its own age buckets",
         "a_label": "Headline tile", "a": tiles["civil"],
         "b_label": "Sum of age buckets", "b": sum(civ_age)},
        {"what": "Cases under 1 year old: national chart vs the state-wise table behind it",
         "a_label": "National chart", "a": age_nat["< 1 yr"],
         "b_label": "State table total", "b": age_tables["0to1"][1]},
        {"what": "Cases at evidence, argument or judgment stage: national chart vs state-wise table",
         "a_label": "National chart", "a": stage_group_nat.get("Evidence/Argument/Judgement", 0),
         "b_label": "State table total", "b": evi_total},
        {"what": "All pending cases: headline tile vs sum of per-state dashboards",
         "a_label": "Headline tile", "a": tiles["total"],
         "b_label": "Sum over states", "b": sum(s["pending"] for s in states)},
        {"what": "Instituted last month: homepage vs state-wise table",
         "a_label": "Homepage", "a": inst_lm[2], "b_label": "State table total", "b": ins_total},
    ]
    checks.append({"what": "All pending cases vs cases that appear in the stage breakdown",
                   "a_label": "All pending", "a": sum(tilde(nat["agewise_count"])),
                   "b_label": "Sum over stages", "b": stage_sum})
    for c in checks:
        c["diff"] = c["b"] - c["a"]
    checks.append({"what": "Pending cases with no stage recorded at all", "a_label": "Cases", "a": blank_stage,
                   "b_label": "Share of pending", "b": None, "diff": None,
                   "note": f"{blank_stage / stage_sum:.1%} of pending cases"})

    out = {
        "source": raw["source"], "fetched_at_utc": raw["fetched_at_utc"],
        "tiles": tiles,
        "last_month": {"instituted": inst_lm, "disposed": disp_lm, "contested": contested_lm,
                       "contested_share": contested_share},
        "flows": flows, "by_filing_year": by_filing,
        "age_national": age_nat,
        "stages_all": stage_all, "stages_criminal": stage_cri, "stage_total": stage_sum,
        "delay_reasons": delay,
        "states": states, "focus": FOCUS,
        "checks": checks,
        "model_defaults": MODEL_DEFAULTS,
    }
    dest = ROOT / "site" / "data.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Console summary so the numbers can be eyeballed against the NJDG site.
    print("tiles", tiles, "| last month in/out", inst_lm[2], disp_lm[2], "| contested share", round(contested_share, 3))
    for f in flows:
        print(f["year"], f["instituted"], f["disposed"], f["instituted"] - f["disposed"])
    print("oldest filing year still pending:", by_filing[0])
    print("top stages:", stage_all[:4], "stage sum", stage_sum)
    for c in checks:
        print("CHECK", c["what"], c["a"], c["b"], c["diff"])
    for s in states:
        if s["state"] in FOCUS:
            print(s["state"], s["pending"], s["ins_2025"], s["disp_2025"], s["witness_stage"], s["older_than_3y"])
    print("saved", dest, dest.stat().st_size, "bytes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else sorted((ROOT / "raw").glob("njdg_*.json"))[-1])
