"""Dev prompt comparison, v1 against v2 on the same records and model (PLAN.md 3.6, hypothesis H2).

  python scripts/compare_prompts.py results/dev_v1_scores.csv results/dev_v2_scores.csv --out results/dev_prompt_comparison.csv

One row per field plus 'overall': match for each prompt, and wrong + unsupported counts (the H2 quantity).
The overall row carries the paired cluster bootstrap of (v2 - v1) overall match from stats.py.
"""
import argparse
from collections import Counter

from common import FIELDS, read_csv, write_csv
from stats import by_record, overall_stat, paired, resamples
from score import rates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    ra, rb = read_csv(args.a), read_csv(args.b)
    ids_a, clusters, ca = by_record(ra)
    ids_b, _, cb = by_record(rb)
    if ids_a != ids_b:
        raise ValueError("score files must cover the same records in the same order")
    pa, pb = ra[0]["prompt"], rb[0]["prompt"]
    out = []
    for f in FIELDS:
        na, nb = Counter(ca[f]), Counter(cb[f])
        out.append({"field": f, "prompt_a": pa, "prompt_b": pb, "match_a": rates(ca[f])["match"],
                    "match_b": rates(cb[f])["match"], "wrong_a": na["wrong"], "wrong_b": nb["wrong"],
                    "unsupported_a": na["unsupported"], "unsupported_b": nb["unsupported"],
                    "omitted_a": na["omitted"], "omitted_b": nb["omitted"],
                    "wrong_plus_unsupported_a": na["wrong"] + na["unsupported"],
                    "wrong_plus_unsupported_b": nb["wrong"] + nb["unsupported"]})
    allix = list(range(len(ids_a)))
    sa, sb = overall_stat(ca), overall_stat(cb)
    total = {k: sum(r[k] for r in out) for k in out[0] if k.startswith(("wrong", "unsupported", "omitted"))}
    out.append({"field": "overall", "prompt_a": pa, "prompt_b": pb, "match_a": sa(allix), "match_b": sb(allix),
                **total, "gap_b_minus_a": sb(allix) - sa(allix), **paired(sb, sa, resamples(clusters))})
    write_csv(args.out, out, list(dict.fromkeys(k for r in out for k in r)))
    for r in out:
        print(r["field"], round(r["match_a"], 3), round(r["match_b"], 3), r["wrong_plus_unsupported_a"],
              r["wrong_plus_unsupported_b"])
    print(out[-1])


if __name__ == "__main__":
    main()
