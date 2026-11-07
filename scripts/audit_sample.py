"""Phase 6 image audit sample (PLAN.md 4, PREREGISTRATION.md section 6).

  python scripts/audit_sample.py results/test_<fast>_scores.csv results/test_<strong>_scores.csv --out results/audit_sample.csv

Pool: every test row scored wrong or unsupported, both models. Up to 60 rows, stratified by field: the pool is
shuffled once per field with random.Random(2026), then fields take turns giving one row each until 60 are
drawn or the pool is empty. The verdict column is left blank for the human adjudicator; the four verdicts are
ai_wrong, record_has_non_label_info, both_defensible, illegible. Copy the file to results/audit_results.csv and
fill the verdict column there; stats.py reads only audit_results.csv.
"""
import argparse
import random

from common import FIELDS, SEED, load_manifest, read_csv, write_csv

MAX_ROWS = 60


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scores", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    urls = {r["gbifID"]: r["image_url"] for r in load_manifest("test")}
    pool = [r for p in a.scores for r in read_csv(p) if r["category"] in ("wrong", "unsupported")]
    rng = random.Random(SEED)
    per_field = {}
    for f in FIELDS:
        rows = sorted((r for r in pool if r["field"] == f), key=lambda r: (r["model"], r["gbifID"]))
        rng.shuffle(rows)
        per_field[f] = rows
    out = []
    while len(out) < MAX_ROWS and any(per_field.values()):
        for f in FIELDS:
            if per_field[f] and len(out) < MAX_ROWS:
                r = per_field[f].pop(0)
                out.append({"gbifID": r["gbifID"], "model": r["model"], "field": f, "category": r["category"],
                            "ai_value": r["ai_value"], "curated_value": r["curated_value"],
                            "image_url": urls[r["gbifID"]], "verdict": "", "note": ""})
    write_csv(a.out, out, list(out[0]))
    print(f"pool {len(pool)} rows; sampled {len(out)} -> {a.out}")


if __name__ == "__main__":
    main()
