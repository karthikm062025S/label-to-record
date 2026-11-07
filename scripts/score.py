"""Field scoring with the pre-registered error taxonomy (PLAN.md 3.4, PREREGISTRATION.md section 2).

Categories: exact, normalized, partial, wrong, unsupported, omitted, both_empty.

Usage:
  python scripts/score.py --split dev --model gemini-2.5-flash --prompt prompts/v1.txt --out results/dev_v1_scores.csv
Reads the cached model responses (results/raw/) for the manifest rows of that split and writes one row per
(record, field). Prints per-field rates and the tier each field falls in.
"""
import argparse
import re
import string
import sys

from common import FIELDS, load_manifest, write_csv

CATEGORIES = ["exact", "normalized", "partial", "wrong", "unsupported", "omitted", "both_empty"]
RANK_TOKENS = {"var.", "subsp.", "f."}
US = {"united states", "united states of america", "usa", "us"}
STATE_VA = {"va", "virginia"}
PUNCT = str.maketrans({c: " " for c in string.punctuation})


def collapse(s):
    return " ".join(str(s).split()) if s is not None else ""


# ---- per-field normalizers -------------------------------------------------------------------

def norm_sciname(s):
    toks = collapse(s).split()
    keep = toks[:2]
    for i in range(2, len(toks) - 1):
        nxt = toks[i + 1]
        if toks[i].lower() in RANK_TOKENS and nxt.isalpha() and nxt.islower():
            keep += [toks[i], nxt]
            break
    return " ".join(keep).lower()


def _person(part):
    """'A. B. Massey' / 'A.B. Massey' / 'Lena Artz' -> 'a b massey' / 'l artz' (initials + surname)."""
    toks = part.replace(".", " ").split()
    if not toks:
        return ""
    return " ".join([t[0] for t in toks[:-1]] + [toks[-1]])


def split_people(s):
    """Split a collector string on , ; & 'and'. A part made only of initials ('Massey, A. B.') is joined
    back to the part before it, written given-names first."""
    parts = [p.strip() for p in re.split(r",|;|&|\band\b", collapse(s).lower()) if p.strip()]
    out = []
    for p in parts:
        if out and all(len(t) == 1 for t in p.replace(".", " ").split()):
            out[-1] = p + " " + out[-1]
        else:
            out.append(p)
    return out


def norm_people(s):
    return frozenset(filter(None, (_person(p) for p in split_people(s))))


def collector_key(s):
    """Normalized collector string: the cap key in sample.py and the bootstrap cluster in stats.py."""
    return "; ".join(sorted(norm_people(s))) or "(none)"


def norm_recnum(s):
    """Strip 'no.', 'no', '#', spaces; lowercase. Every unnumbered form (s.n., sn, s n, empty) becomes ''."""
    s = re.sub(r"^(no\.?|#)\s*", "", collapse(s).lower())
    s = re.sub(r"\s", "", s)
    return "" if s.replace(".", "") == "sn" else s


def parse_date(s):
    """-> (year, month, day) with None for missing parts, or None if not ISO-like.
    A GBIF range 'a/b' is read as its start; a time part is dropped."""
    s = collapse(s).split("/")[0].split("T")[0]
    m = re.fullmatch(r"(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?", s)
    if not m:
        return None
    return tuple(int(x) if x else None for x in m.groups())


def norm_country(s):
    s = collapse(s.replace(".", "")).lower()
    return "united states" if s in US else s


def norm_state(s):
    s = collapse(s.replace(".", "")).lower()
    return "virginia" if s in STATE_VA else s


def norm_county(s):
    return re.sub(r"\s+(county|co\.?)$", "", collapse(s).lower()).strip()


def norm_text(s):
    return collapse(str(s).lower().translate(PUNCT))


def jaccard(a, b):
    a, b = set(a.split()), set(b.split())
    return len(a & b) / len(a | b) if a | b else 0.0


# ---- the classifier ---------------------------------------------------------------------------

def score_field(field, ai, cur):
    ai, cur = collapse(ai), collapse(cur)
    if field == "recordNumber":
        a, c = norm_recnum(ai), norm_recnum(cur)
        if not cur:   # no curated value: not scorable, whatever the AI wrote
            return "both_empty" if not a else "unsupported"
        if a == c:    # s.n., sn, s n and null are one value, "unnumbered": AI null vs curated s.n. matches
            return "exact" if ai == cur else "normalized"
        return "omitted" if not ai else "wrong"
    if not ai and not cur:
        return "both_empty"
    if not ai:
        return "omitted"
    if not cur:
        return "unsupported"
    if ai == cur:
        return "exact"
    if field == "scientificName":
        if norm_sciname(ai) == norm_sciname(cur):
            return "normalized"
        return "partial" if ai.split()[0].lower() == cur.split()[0].lower() else "wrong"
    if field == "recordedBy":
        a, c = norm_people(ai), norm_people(cur)
        if a == c:
            return "normalized"
        return "partial" if {p.split()[-1] for p in a} & {p.split()[-1] for p in c} else "wrong"
    if field == "eventDate":
        a, c = parse_date(ai), parse_date(cur)
        if a is None or c is None:
            return "wrong"
        if a == c:
            return "normalized"
        same = all(x == y for x, y in zip(a, c) if x is not None and y is not None)
        return "partial" if a[0] == c[0] and same else "wrong"
    if field in ("country", "stateProvince", "county"):
        f = {"country": norm_country, "stateProvince": norm_state, "county": norm_county}[field]
        return "normalized" if f(ai) == f(cur) else "wrong"
    if field in ("locality", "habitat"):
        a, c = norm_text(ai), norm_text(cur)
        if a == c:
            return "normalized"
        return "partial" if jaccard(a, c) >= 0.5 or a in c or c in a else "wrong"
    raise ValueError(field)


def rates(categories):
    """categories: list of category strings for one field -> dict of pre-registered rates (None if no denominator)."""
    n = {k: categories.count(k) for k in CATEGORIES}
    scorable = len(categories) - n["unsupported"] - n["both_empty"]
    empty_cur = n["unsupported"] + n["both_empty"]
    div = lambda a, b: a / b if b else None
    return {"n_scorable": scorable, "n_curated_empty": empty_cur, **{"n_" + k: v for k, v in n.items()},
            "match": div(n["exact"] + n["normalized"], scorable), "partial": div(n["partial"], scorable),
            "wrong": div(n["wrong"], scorable), "omitted": div(n["omitted"], scorable),
            "unsupported": div(n["unsupported"], empty_cur)}


def tier(match, wrong, omitted, audited_halluc):
    """PREREGISTRATION.md section 2 rules as written. audited_halluc None = audit missing, so auto_fill is
    impossible and a field that would have reached it reads 'assist (audit missing)'."""
    if match is None:
        return "not_scorable"
    if match >= 0.95 and wrong <= 0.01:
        if audited_halluc is None:
            return "assist (audit missing)"
        if audited_halluc <= 0.01:
            return "auto_fill"
    if match < 0.80 or wrong > 0.05 or omitted > 0.50:
        return "do_not_use"
    return "assist"


def score_rows(split, model, prompt_path):
    """One row per (record, field), read from the run_model cache. A record whose call failed every retry is
    scored omitted for every field with api_error=1, so the failure counts against the tool (PLAN.md 4)."""
    from run_model import load_cached  # local import keeps the test file free of network code
    out = []
    for row in load_manifest(split):
        pred, err = load_cached(model, prompt_path, row["gbifID"])
        for f in FIELDS:
            ai = None if err else (pred or {}).get(f)
            cat = score_field(f, ai, row[f])
            if err and cat != "both_empty":
                cat = "omitted"
            out.append({"gbifID": row["gbifID"], "split": split, "model": model, "prompt": prompt_path,
                        "field": f, "ai_value": "" if ai is None else ai, "curated_value": row[f],
                        "category": cat, "api_error": int(bool(err)),
                        "cluster": collector_key(row["recordedBy"])})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = score_rows(a.split, a.model, a.prompt)
    write_csv(a.out, rows, list(rows[0].keys()))
    print(f"{'field':15} {'n':>3} {'match':>6} {'part':>6} {'wrong':>6} {'omit':>6} {'unsup':>6}  tier")
    fmt = lambda v: "  -   " if v is None else f"{v:6.3f}"
    matches = []
    for f in FIELDS:
        r = rates([x["category"] for x in rows if x["field"] == f])
        if r["match"] is not None:
            matches.append(r["match"])
        t = tier(r["match"], r["wrong"], r["omitted"], None)
        print(f"{f:15} {r['n_scorable']:3} {fmt(r['match'])} {fmt(r['partial'])} {fmt(r['wrong'])} "
              f"{fmt(r['omitted'])} {fmt(r['unsupported'])}  {t}")
    print(f"overall match (unweighted mean of {len(matches)} fields): {sum(matches) / len(matches):.3f}")
    print(f"wrote {a.out} ({len(rows)} rows)")


if __name__ == "__main__":
    sys.exit(main())
