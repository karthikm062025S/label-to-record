"""Derived numbers for REPORT.md that are not already a column of test_summary.csv or model_comparison.csv.

  python scripts/report_numbers.py --out results/report_numbers.csv

One row per number: name, value, numerator, denominator, source file, and kind ('preregistered' or 'post_hoc').
Post-hoc rows are diagnostics written after seeing test results; they never change a tier or a gate verdict.
"""
import argparse
import json
import re
import statistics

from common import FIELDS, RESULTS, load_manifest, read_csv, write_csv
from run_model import cache_path
from score import norm_people, norm_text

MODELS = ["gemini-3-flash-preview", "gemini-3.1-pro-preview"]
STRONG = MODELS[1]
PROMPT = "prompts/v2.txt"


def add(out, name, num, den=None, source="", kind="preregistered"):
    val = num / den if den else num
    out.append({"name": name, "value": round(val, 4) if isinstance(val, float) else val,
                "numerator": num if den else "", "denominator": den or "", "source": source, "kind": kind})


def surname_first(s):
    """'Wieboldt, Thomas F.; Croy, S. Q.' -> 'Thomas F. Wieboldt; S. Q. Croy' (post-hoc diagnostic only)."""
    parts = []
    for p in re.split(r";", s):
        bits = [b.strip() for b in p.split(",")]
        bits = [b for b in bits if b and b.lower().rstrip(".") not in ("jr", "sr")]
        parts.append(f"{bits[1]} {bits[0]}" if len(bits) == 2 else p)
    return "; ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = []
    test = load_manifest("test")
    for m in MODELS:
        src = f"results/test_{m}_scores.csv"
        rows = read_csv(RESULTS / f"test_{m}_scores.csv")
        for cat in ("wrong", "unsupported", "omitted", "partial"):
            add(out, f"{m} total {cat} (all fields)", sum(r["category"] == cat for r in rows), source=src)
        empty = [r for r in rows if r["category"] in ("unsupported", "both_empty")]
        add(out, f"{m} pooled unsupported rate (AI filled / curated empty, all fields; unaudited upper bound)",
            sum(r["category"] == "unsupported" for r in empty), len(empty), src, "post_hoc")
        filled = [r for r in rows if r["ai_value"]]
        add(out, f"{m} wrong + unsupported share of AI-filled values (AI-filled = ai_value non-empty, incl. 's.n.')",
            sum(r["category"] in ("wrong", "unsupported") for r in filled), len(filled), src, "post_hoc")
        nulls = sum(all(not r["ai_value"] for r in rows if r["gbifID"] == t["gbifID"]) for t in test)
        add(out, f"{m} records with every field null", nulls, source=src)
        recs = [json.loads(cache_path(m, PROMPT, t["gbifID"]).read_text(encoding="utf-8")) for t in test]
        lat = [r["latency_s"] for r in recs]
        use = [r["response"].get("usageMetadata", {}) for r in recs]
        src_raw = "results/raw/*.json (test, prompts/v2.txt)"
        add(out, f"{m} test calls (attempts)", sum(r["attempts"] for r in recs), source=src_raw)
        add(out, f"{m} median latency s", statistics.median(lat), source=src_raw)
        add(out, f"{m} mean prompt tokens", sum(u.get("promptTokenCount", 0) for u in use), len(use), src_raw)
        add(out, f"{m} mean output tokens", sum(u.get("candidatesTokenCount", 0) for u in use), len(use), src_raw)
        add(out, f"{m} mean thinking tokens", sum(u.get("thoughtsTokenCount", 0) for u in use), len(use), src_raw)
        # Post-hoc: recordedBy 'partial' rows that are only the record's 'Surname, Given' order.
        rb = [r for r in rows if r["field"] == "recordedBy" and r["category"] == "partial"]
        same = sum(norm_people(r["ai_value"]) == norm_people(surname_first(r["curated_value"])) for r in rb)
        add(out, f"{m} recordedBy partial rows that match after reordering 'Surname, Given'", same, len(rb), src,
            "post_hoc")
        # Post-hoc: habitat omitted rows whose curated habitat text appears inside the AI locality.
        loc = {r["gbifID"]: norm_text(r["ai_value"]) for r in rows if r["field"] == "locality"}
        ho = [r for r in rows if r["field"] == "habitat" and r["category"] == "omitted"]
        moved = sum(norm_text(r["curated_value"]) in loc[r["gbifID"]] for r in ho)
        add(out, f"{m} habitat omitted rows whose curated habitat is inside the AI locality", moved, len(ho), src,
            "post_hoc")
    tag = f"test_{STRONG}"
    gb = read_csv(RESULTS / f"reconcile_gbif_{tag}.csv")
    src = f"results/reconcile_gbif_{tag}.csv"
    filled = [r for r in gb if r["ai_scientificName"]]
    add(out, "gate4 GBIF: AI accepted key equals curated, where AI name not omitted",
        sum(r["ai_reconciled"] == "1" for r in filled), len(filled), src)
    add(out, "gate4 GBIF control: curated name reconciles to its own accepted key",
        sum(r["curated_reconciled"] == "1" for r in gb), len(gb), src)
    for cat in ("wrong", "partial"):
        rs = [r for r in gb if r["string_category"] == cat]
        add(out, f"H4: strong {cat} scientificName that reconcile to the curated accepted key",
            sum(r["ai_reconciled"] == "1" for r in rs), len(rs), src, "preregistered" if cat == "wrong" else "post_hoc")
    st = [r for r in gb if r["string_category"] in ("exact", "normalized")]
    add(out, "strong string-match scientificName that also reconcile", sum(r["ai_reconciled"] == "1" for r in st),
        len(st), src, "post_hoc")
    tg = read_csv(RESULTS / f"reconcile_tgn_{tag}.csv")
    lc = read_csv(RESULTS / f"reconcile_lcnaf_{tag}.csv")
    for who in ("curated", "ai"):
        t = [r for r in tg if r["source"] == who]
        add(out, f"gate4 TGN: distinct {who} county strings resolving to one Virginia county",
            sum(r["resolved"] == "1" for r in t), len(t), f"results/reconcile_tgn_{tag}.csv")
        strings = {r["recordedBy"] for r in lc if r["source"] == who}
        cov = {r["recordedBy"] for r in lc if r["source"] == who and r["covered"] == "1"}
        add(out, f"gate4 LC NAF: distinct {who} collector strings with a plausible hit (any one person in the string)",
            len(cov), len(strings), f"results/reconcile_lcnaf_{tag}.csv")
        miss = {r["recordedBy"] for r in lc if r["source"] == who and r["covered"] != "1"}
        add(out, f"LC NAF: distinct {who} collector strings where every person has a plausible hit",
            len(strings - miss), len(strings), f"results/reconcile_lcnaf_{tag}.csv", "post_hoc")
        people = {r["person"] for r in lc if r["source"] == who}
        pcov = {r["person"] for r in lc if r["source"] == who and r["covered"] == "1"}
        add(out, f"LC NAF: distinct {who} normalized persons with a plausible hit", len(pcov), len(people),
            f"results/reconcile_lcnaf_{tag}.csv", "post_hoc")
    write_csv(a.out, out, ["name", "value", "numerator", "denominator", "source", "kind"])
    for r in out:
        print(r["kind"][:4], r["name"], "=", r["value"], f"({r['numerator']}/{r['denominator']})" if r["denominator"] else "")


if __name__ == "__main__":
    main()
