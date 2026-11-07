"""Phase 1: draw and freeze the 100-record sample and the 30/70 dev/test split (PLAN.md 3.1).

  python scripts/sample.py

Writes data/manifest.csv (the frozen sample), data/sample_log.csv (every draw and why it was kept or
rejected) and results/manifest_stats.csv (decade, family and collector counts per split). GBIF result order
can change, so a rerun on another day can draw different records. Later phases read the committed manifest,
never a fresh draw. The script refuses to overwrite an existing manifest unless --force is given.
"""
import argparse
import json
import random
import sys
from collections import Counter

from common import DATA, FIELDS, MANIFEST, RESULTS, SEED, http_get, qs, write_csv
from score import collector_key

API = "https://api.gbif.org/v1/occurrence/search"
POOL = dict(institutionCode="VPI", country="US", stateProvince="Virginia", basisOfRecord="PRESERVED_SPECIMEN",
            mediaType="StillImage", kingdomKey=6, year="1700,2026")
N_DRAW, N_ACCEPT, N_DEV = 160, 100, 30
CAP = {"collector": 8, "family": 8, "decade": 20}
LICENSES = {"http://creativecommons.org/licenses/by/4.0/legalcode": "CC BY 4.0",
            "http://creativecommons.org/licenses/by-nc/4.0/legalcode": "CC BY-NC 4.0"}
COLUMNS = ["gbifID", "catalogNumber", "occurrenceID", "split", "image_url", "license", "family", "year",
           "scientificName", "acceptedScientificName", "taxonKey", "acceptedTaxonKey", "recordedBy",
           "recordNumber", "eventDate", "verbatimEventDate", "country", "stateProvince", "county", "locality",
           "habitat"]


def gbif(**params):
    status, _, body = http_get(API + "?" + qs(**POOL, **params))
    if status != 200:
        raise RuntimeError(f"GBIF HTTP {status}: {body[:200]!r}")
    return json.loads(body)


def image_ok(url):
    """HEAD, then GET on failure: HTTP 200 and Content-Type image/*. -> (ok, detail)."""
    for method in ("HEAD", "GET"):
        try:
            status, headers, _ = http_get(url, method=method, timeout=60, retries=2)
        except Exception as e:  # network failure on this method; try the next one
            status, headers = repr(e)[:80], {}
        ctype = {k.lower(): v for k, v in headers.items()}.get("content-type", "")
        if status == 200 and ctype.startswith("image/"):
            return True, f"{method} 200 {ctype}"
    return False, f"{method} {status} {ctype}"


def decade(year):
    return f"{int(year) // 10 * 10}s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite an existing manifest")
    ap.add_argument("--draws", type=int, default=N_DRAW,
                    help="oversample size. random.sample with one seed is prefix-stable here (checked: the first "
                         "160 of 400 equal the 160-draw), so a larger value only adds draws after the first 160")
    args = ap.parse_args()
    if MANIFEST.exists() and not args.force:
        sys.exit(f"{MANIFEST} exists and is the frozen sample; pass --force to redraw")
    pool_count = gbif(limit=0)["count"]
    offsets = random.Random(SEED).sample(range(pool_count), args.draws)
    log, accepted, used = [], [], {k: Counter() for k in CAP}
    for i, off in enumerate(offsets):
        if len(accepted) == N_ACCEPT:
            break
        res = gbif(limit=1, offset=off)["results"]
        rec = res[0] if res else {}
        media = [m for m in rec.get("media", []) if m.get("type") == "StillImage" and m.get("identifier")]
        keys = {"collector": collector_key(rec.get("recordedBy", "")), "family": rec.get("family") or "(none)",
                "decade": decade(rec["year"]) if rec.get("year") else "(none)"}
        reason = ""
        if not rec:
            reason = "no record at offset"
        elif not rec.get("recordedBy") or not rec.get("eventDate"):
            reason = "missing recordedBy or eventDate"
        elif not media:
            reason = "no StillImage media"
        elif rec.get("license") not in LICENSES:
            reason = f"license not allowed: {rec.get('license')}"
        elif any(r["gbifID"] == str(rec["gbifID"]) for r in accepted):
            reason = "duplicate gbifID"
        else:
            over = [k for k in CAP if used[k][keys[k]] >= CAP[k]]
            if over:
                reason = "cap: " + ",".join(f"{k}={keys[k]}" for k in over)
            else:
                ok, detail = image_ok(media[0]["identifier"])
                if not ok:
                    reason = "image check failed: " + detail
        log.append({"draw": i, "offset": off, "gbifID": rec.get("gbifID", ""),
                    "decision": "reject" if reason else "accept", "reason": reason, **keys})
        if reason:
            continue
        for k in CAP:
            used[k][keys[k]] += 1
        row = {c: rec.get(c, "") for c in COLUMNS}
        row.update(gbifID=str(rec["gbifID"]), image_url=media[0]["identifier"], license=LICENSES[rec["license"]])
        accepted.append(row)
        print(f"draw {i:3}: accepted {len(accepted)}")
    write_csv(DATA / "sample_log.csv", log, list(log[0].keys()))
    if len(accepted) < N_ACCEPT:
        sys.exit(f"only {len(accepted)} accepted from {args.draws} draws; see data/sample_log.csv. "
                 "Not writing a manifest: extending the draw is a protocol change (PREREGISTRATION.md amendment).")
    ids = [r["gbifID"] for r in accepted]
    random.Random(SEED).shuffle(ids)
    split = {g: ("dev" if j < N_DEV else "test") for j, g in enumerate(ids)}
    for r in accepted:
        r["split"] = split[r["gbifID"]]
    write_csv(MANIFEST, accepted, COLUMNS)
    stats = [{"dimension": "pool_count", "value": pool_count, "dev": "", "test": "", "total": pool_count},
             {"dimension": "draws_used", "value": len(log), "dev": "", "test": "", "total": len(log)}]
    for dim, key in (("decade", lambda r: decade(r["year"])), ("family", lambda r: r["family"]),
                     ("collector", lambda r: collector_key(r["recordedBy"])), ("license", lambda r: r["license"])):
        c = {s: Counter(key(r) for r in accepted if r["split"] == s) for s in ("dev", "test")}
        for v in sorted(set(c["dev"]) | set(c["test"])):
            stats.append({"dimension": dim, "value": v, "dev": c["dev"][v], "test": c["test"][v],
                          "total": c["dev"][v] + c["test"][v]})
    rejects = Counter(x["reason"].split(":")[0] for x in log if x["reason"])
    stats += [{"dimension": "reject_reason", "value": k, "dev": "", "test": "", "total": v}
              for k, v in sorted(rejects.items())]
    write_csv(RESULTS / "manifest_stats.csv", stats, ["dimension", "value", "dev", "test", "total"])
    print(f"pool {pool_count}; {len(log)} draws; {len(accepted)} accepted; rejects {dict(rejects)}")
    assert set(FIELDS) <= set(COLUMNS)


if __name__ == "__main__":
    main()
