"""Print the markdown tables in REPORT.md from the results files, so no table number is typed by hand.

  python scripts/report_tables.py

Rates are the file value x 100, rounded to one decimal. CIs are the clustered 95% bootstrap from test_summary.csv.
"""
from common import FIELDS, RESULTS, read_csv

MODELS = [("gemini-3.1-pro-preview", "strong"), ("gemini-3-flash-preview", "fast")]


def p(v):
    return "-" if v in ("", None) else f"{float(v) * 100:.1f}"


def ci(r, k):
    return f"{p(r[k + '_ci_low'])} to {p(r[k + '_ci_high'])}" if r.get(k + "_ci_low") else "-"


def main():
    s = {(r["model"], r["field"]): r for r in read_csv(RESULTS / "test_summary.csv")}
    print("Per field, test, both models (source: results/test_summary.csv)\n")
    print("| Field | Model | scorable n | match % (95% CI) | partial % | wrong % (95% CI) | omitted % | unsupported (n / curated empty) | tier |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for f in FIELDS:
        for m, lab in MODELS:
            r = s[(m, f)]
            print(f"| {f} | {lab} | {r['n_scorable']} | {p(r['match'])} ({ci(r, 'match')}) | {p(r['partial'])} | "
                  f"{p(r['wrong'])} ({ci(r, 'wrong')}) | {p(r['omitted'])} | {r['n_unsupported']} / {r['n_curated_empty']} | {r['tier']} |")
    print("\nOverall match, unweighted mean of nine fields (source: results/test_summary.csv)\n")
    print("| Model | overall match % | 95% CI, clustered by collector | 95% CI, per record |")
    print("| --- | --- | --- | --- |")
    for m, lab in MODELS:
        r = s[(m, "overall")]
        print(f"| {lab} ({m}) | {p(r['match'])} | {ci(r, 'match')} | {p(r['match_ci_low_unclustered'])} to "
              f"{p(r['match_ci_high_unclustered'])} |")
    c = read_csv(RESULTS / "model_comparison.csv")[0]
    print("\nModel comparison (source: results/model_comparison.csv)\n")
    print("| gap strong minus fast, points | 95% CI | two-sided p | CI excludes 0 |")
    print("| --- | --- | --- | --- |")
    print(f"| {p(c['gap'])} | {p(c['ci_low'])} to {p(c['ci_high'])} | {float(c['p_two_sided']):.3f} | {c['excludes_zero']} |")
    print("\nDerived numbers (source: results/report_numbers.csv)\n")
    print("| Number | value | n / d | kind |")
    print("| --- | --- | --- | --- |")
    for r in read_csv(RESULTS / "report_numbers.csv"):
        v = r["value"]
        nd = f"{r['numerator']} / {r['denominator']}" if r["denominator"] else ""
        val = p(v) + "%" if r["denominator"] and "mean" not in r["name"] else v
        print(f"| {r['name']} | {val} | {nd} | {r['kind']} |")


if __name__ == "__main__":
    main()
