"""95% percentile bootstrap CIs, clustered by collector, and the paired model comparison (PLAN.md 3.5).

Ported from the author's earlier research code (top1_ci, paired_bootstrap, p_floor) to
stdlib random: resample clusters with replacement, keep every record of a drawn cluster, recompute the
statistic; the paired version applies the SAME resample to both models before differencing. Clusters are
normalized collector strings: one collector's sheets share one hand and one label style.

  python scripts/stats.py --scores results/test_<fast>_scores.csv results/test_<strong>_scores.csv \
      --strong <strong model> --summary results/test_summary.csv --comparison results/model_comparison.csv
"""
import argparse
import random
from collections import defaultdict
from pathlib import Path

from common import FIELDS, RESULTS, SEED, read_csv, write_csv
from score import rates, tier

N_BOOT = 10000


def resamples(clusters, n_boot=N_BOOT, seed=SEED, clustered=True):
    """Index lists, one per bootstrap draw. clustered=False resamples single records."""
    if not clustered:
        clusters = list(range(len(clusters)))
    groups = defaultdict(list)
    for i, c in enumerate(clusters):
        groups[c].append(i)
    keys = list(groups)
    rng = random.Random(seed)
    return [[i for _ in keys for i in groups[keys[rng.randrange(len(keys))]]] for _ in range(n_boot)]


def percentile(sorted_vals, q):
    """Linear interpolation, the numpy default, so CIs match the ported numpy code."""
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def ci(stat, draws):
    """stat(index list) -> float or None. Draws where the statistic is undefined are dropped and counted."""
    vals = sorted(v for v in (stat(ix) for ix in draws) if v is not None)
    if not vals:
        return None, None, len(draws)
    return percentile(vals, 0.025), percentile(vals, 0.975), len(draws) - len(vals)


def p_floor(n_boot):
    return 2.0 / (n_boot + 1)


def paired(stat_a, stat_b, draws):
    """Gap A-B on the same resamples: CI, two-sided p with the add-one correction, and the floor flag."""
    diffs = [a - b for a, b in ((stat_a(ix), stat_b(ix)) for ix in draws) if a is not None and b is not None]
    n_le, n_ge = sum(d <= 0 for d in diffs), sum(d >= 0 for d in diffs)
    s = sorted(diffs)
    lo, hi = percentile(s, 0.025), percentile(s, 0.975)
    return {"ci_low": lo, "ci_high": hi, "n_boot": len(diffs),
            "p_two_sided": min(1.0, 2.0 * (min(n_le, n_ge) + 1) / (len(diffs) + 1)),
            "p_is_floor": min(n_le, n_ge) == 0, "p_floor_value": p_floor(len(diffs)),
            "excludes_zero": lo > 0 or hi < 0}


def rate_stat(cats, name):
    """cats: per-record category list for one field -> function(index list) -> that rate on the resample."""
    return lambda ix: rates([cats[i] for i in ix])[name]


def overall_stat(cats_by_field):
    def f(ix):
        ms = [rates([cats_by_field[fl][i] for i in ix])["match"] for fl in FIELDS]
        ms = [m for m in ms if m is not None]
        return sum(ms) / len(ms) if ms else None
    return f


def by_record(rows):
    """scores rows -> (gbifIDs in order, clusters, {field: [category per record]})."""
    ids, clusters, cats = [], [], defaultdict(list)
    for r in rows:
        if r["field"] == FIELDS[0]:
            ids.append(r["gbifID"])
            clusters.append(r["cluster"])
        cats[r["field"]].append(r["category"])
    return ids, clusters, cats


def audited_halluc(model, field, path=RESULTS / "audit_results.csv"):
    """Share of audited wrong/unsupported rows judged ai_wrong, or None when the audit is missing.
    Columns expected: gbifID, model, field, category, verdict."""
    if not Path(path).exists():
        return None
    rows = [r for r in read_csv(path) if r["model"] == model and r["field"] == field
            and r["category"] in ("wrong", "unsupported") and r["verdict"]]
    return sum(r["verdict"] == "ai_wrong" for r in rows) / len(rows) if rows else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", nargs="+", required=True, help="one scores CSV per model, same split")
    ap.add_argument("--strong", help="model name of the strong model (for the comparison)")
    ap.add_argument("--summary", required=True)
    ap.add_argument("--comparison")
    a = ap.parse_args()
    per_model = {}
    for path in a.scores:
        rows = read_csv(path)
        per_model[rows[0]["model"]] = by_record(rows)
    ids0 = next(iter(per_model.values()))[0]
    if any(v[0] != ids0 for v in per_model.values()):
        raise ValueError("score files must cover the same records in the same order")
    clusters = next(iter(per_model.values()))[1]
    draws = {"cluster": resamples(clusters), "record": resamples(clusters, clustered=False)}
    summary = []
    for model, (_, _, cats) in per_model.items():
        for f in FIELDS + ["overall"]:
            out = {"model": model, "field": f, "n_records": len(ids0), "n_clusters": len(set(clusters))}
            if f == "overall":
                stat = overall_stat(cats)
                out["match"] = stat(list(range(len(ids0))))
                out["match_ci_low"], out["match_ci_high"], _ = ci(stat, draws["cluster"])
                out["match_ci_low_unclustered"], out["match_ci_high_unclustered"], _ = ci(stat, draws["record"])
            else:
                r = rates(cats[f])
                out.update(r)
                for name in ("match", "wrong", "omitted", "unsupported"):
                    lo, hi, dropped = ci(rate_stat(cats[f], name), draws["cluster"])
                    out[f"{name}_ci_low"], out[f"{name}_ci_high"] = lo, hi
                    out[f"{name}_ci_dropped_draws"] = dropped
                out["match_ci_low_unclustered"], out["match_ci_high_unclustered"], _ = ci(
                    rate_stat(cats[f], "match"), draws["record"])
                h = audited_halluc(model, f)
                out["audited_halluc"] = h
                out["audit"] = "present" if h is not None else "missing"
                out["tier"] = tier(r["match"], r["wrong"], r["omitted"], h)
            summary.append(out)
            print(model, f, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()
                             if k in ("match", "match_ci_low", "match_ci_high", "tier")})
    cols = list(dict.fromkeys(k for s in summary for k in s))
    write_csv(a.summary, summary, cols)
    if a.comparison:
        fast = [m for m in per_model if m != a.strong]
        if a.strong not in per_model or len(fast) != 1:
            raise ValueError("--comparison needs exactly two models and --strong naming one of them")
        sa, sb = overall_stat(per_model[a.strong][2]), overall_stat(per_model[fast[0]][2])
        allix = list(range(len(ids0)))
        comp = {"strong": a.strong, "fast": fast[0], "gap": sa(allix) - sb(allix), "clustered": True,
                **paired(sa, sb, draws["cluster"])}
        write_csv(a.comparison, [comp], list(comp))
        print(comp)


if __name__ == "__main__":
    main()
