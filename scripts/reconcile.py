"""Reconcile names and places against controlled vocabularies (PLAN.md 3.8, PREREGISTRATION.md section 4).

  python scripts/reconcile.py --probe                 one known input per endpoint (phase 4 gate)
  python scripts/reconcile.py --scores results/test_<strong>_scores.csv   writes results/reconcile_*.csv

Every response is cached under results/vocab_cache/<service>/ (keyed by URL), so a rerun makes no requests.
- GBIF backbone: species/match on a name; reconciled = accepted key equals the curated acceptedTaxonKey.
- Getty TGN: one SPARQL query lists every TGN place whose preferred parent is Virginia (tgn:7007919, found by
  probe 2026-11-06: label 'Virginia', type states aat:300000776, parent 'United States'); a county string
  resolves when exactly one TGN place of type counties (aat:300000771) has that label after county
  normalization.
- LC Name Authority File: suggest2 keyword search on the normalized name; a plausible hit is a label whose
  'Surname, Given' heading normalizes to the same initials and surname.
"""
import argparse
from collections import defaultdict

from common import RESULTS, get_json_cached, load_manifest, qs, read_csv, write_csv
from score import _person, norm_county, norm_people

CACHE = RESULTS / "vocab_cache"
VIRGINIA_TGN = "7007919"
COUNTIES_AAT = "300000771"
TGN_QUERY = ("select ?place ?label ?type where { ?place skos:inScheme tgn: ; gvp:broaderPreferred tgn:%s ; "
             "gvp:prefLabelGVP/xl:literalForm ?label ; gvp:placeTypePreferred ?type . }" % VIRGINIA_TGN)


def gbif_match(name):
    d = get_json_cached("https://api.gbif.org/v1/species/match?" + qs(name=name), CACHE / "gbif")
    return {"usageKey": d.get("usageKey"), "acceptedUsageKey": d.get("acceptedUsageKey") or d.get("usageKey"),
            "matchType": d.get("matchType"), "confidence": d.get("confidence"), "status": d.get("status"),
            "matched_name": d.get("scientificName")}


def tgn_counties():
    """{normalized county label: [TGN ids]} for TGN counties under Virginia (one request, cached)."""
    url = "https://vocab.getty.edu/sparql.json?" + qs(query=TGN_QUERY)
    d = get_json_cached(url, CACHE / "tgn", headers={"Accept": "application/sparql-results+json"})
    out = defaultdict(list)
    for b in d["results"]["bindings"]:
        if b["type"]["value"].endswith(COUNTIES_AAT):
            out[norm_county(b["label"]["value"])].append(b["place"]["value"].rsplit("/", 1)[-1])
    return out


def tgn_resolve(county, table):
    ids = table.get(norm_county(county), [])
    return ids[0] if len(ids) == 1 else None, len(ids)


def lc_heading_person(label):
    """'Massey, A. B. (Arthur Ballard), 1889-1982' -> 'a b massey'."""
    head = label.split("(")[0]
    parts = [p.strip() for p in head.split(",")]
    if len(parts) >= 2 and parts[1] and not parts[1][0].isdigit():
        return _person(f"{parts[1]} {parts[0]}".lower())
    return _person(parts[0].lower())


def lc_lookup(person):
    """person: one normalized name like 'a b massey'. -> (hit count, plausible hit label, uri)."""
    url = "https://id.loc.gov/authorities/names/suggest2?" + qs(q=person, count=10, searchtype="keyword")
    d = get_json_cached(url, CACHE / "lcnaf")
    for h in d.get("hits", []):
        if lc_heading_person(h.get("aLabel") or h.get("suggestLabel", "")) == person:
            return len(d.get("hits", [])), h.get("aLabel"), h.get("uri")
    return len(d.get("hits", [])), "", ""


def probe():
    m = gbif_match("Arabis lyrata L.")
    print("GBIF match 'Arabis lyrata L.':", m)
    table = tgn_counties()
    print(f"TGN: {sum(len(v) for v in table.values())} counties under Virginia; 'Montgomery County' ->",
          tgn_resolve("Montgomery County", table))
    print("LC NAF 'a b massey':", lc_lookup("a b massey"))


def run(scores_path):
    rows = read_csv(scores_path)
    model = rows[0]["model"]
    curated = {r["gbifID"]: r for r in load_manifest(rows[0]["split"])}
    ai = defaultdict(dict)
    for r in rows:
        ai[r["gbifID"]][r["field"]] = r["ai_value"]
    tag = f"{rows[0]['split']}_{model}"
    gb = []
    for g, fields in ai.items():
        cur = curated[g]
        out = {"gbifID": g, "model": model, "curated_acceptedTaxonKey": cur["acceptedTaxonKey"],
               "curated_scientificName": cur["scientificName"], "ai_scientificName": fields["scientificName"],
               "string_category": next(r["category"] for r in rows
                                       if r["gbifID"] == g and r["field"] == "scientificName")}
        for who in ("ai", "curated"):
            name = fields["scientificName"] if who == "ai" else cur["scientificName"]
            m = gbif_match(name) if name else {}
            out[f"{who}_acceptedUsageKey"] = m.get("acceptedUsageKey")
            out[f"{who}_matchType"] = m.get("matchType")
            out[f"{who}_reconciled"] = int(bool(name) and str(m.get("acceptedUsageKey")) == cur["acceptedTaxonKey"])
        gb.append(out)
    write_csv(RESULTS / f"reconcile_gbif_{tag}.csv", gb, list(gb[0]))
    table = tgn_counties()
    tg = []
    for who in ("ai", "curated"):
        values = {(fields["county"] if who == "ai" else curated[g]["county"]) for g, fields in ai.items()}
        for v in sorted(x for x in values if x):
            tid, n = tgn_resolve(v, table)
            tg.append({"source": who, "county": v, "tgn_id": tid or "", "n_candidates": n, "resolved": int(bool(tid))})
    write_csv(RESULTS / f"reconcile_tgn_{tag}.csv", tg, list(tg[0]))
    lc = []
    for who in ("ai", "curated"):
        values = {(fields["recordedBy"] if who == "ai" else curated[g]["recordedBy"]) for g, fields in ai.items()}
        for v in sorted(x for x in values if x):
            for person in sorted(norm_people(v)):
                n, label, uri = lc_lookup(person)
                lc.append({"source": who, "recordedBy": v, "person": person, "n_hits": n,
                           "plausible_label": label, "uri": uri, "covered": int(bool(uri))})
    write_csv(RESULTS / f"reconcile_lcnaf_{tag}.csv", lc, list(lc[0]))
    for name, rs, col in (("gbif ai", gb, "ai_reconciled"), ("gbif curated", gb, "curated_reconciled")):
        print(name, sum(int(r[col]) for r in rs), "/", len(rs))
    for who in ("ai", "curated"):
        t = [r for r in tg if r["source"] == who]
        l = [r for r in lc if r["source"] == who]
        strings = {r["recordedBy"] for r in l}
        covered = {r["recordedBy"] for r in l if r["covered"]}
        print(f"tgn {who}: {sum(r['resolved'] for r in t)}/{len(t)} distinct counties resolved | lcnaf {who}: "
              f"{len(covered)}/{len(strings)} distinct collector strings with a plausible hit")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--scores")
    a = ap.parse_args()
    if a.probe:
        probe()
    if a.scores:
        run(a.scores)


if __name__ == "__main__":
    main()
