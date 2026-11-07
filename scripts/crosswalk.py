"""Darwin Core -> simple Dublin Core crosswalk and export (PLAN.md 3.9).

  python scripts/crosswalk.py --split test --source model --model <strong> --prompt prompts/v2.txt --out results/dublin_core.csv
  python scripts/crosswalk.py --split test --source curated --out results/dublin_core_curated.csv

One row per record. Multi-valued elements (dc:identifier, dc:coverage parts) are joined with ' | '.
recordedBy maps to dc:creator: the collector made the specimen. A cultural-heritage profile might prefer
dc:contributor; that choice is a profile decision, stated in REPORT.md, not made here.

One-to-one principle (DCMI): a record describes one resource. Each row describes the physical specimen
(dc:type PhysicalObject). The sheet photograph is a separate resource, so it is not described here with
dc:format; its URL is linked as dcterms:hasFormat (the same specimen in another format). A full profile would
give the image its own record (dc:type StillImage, dc:format image/jpeg).
"""
import argparse

from common import load_manifest, write_csv

DC = ["dc:title", "dc:subject", "dc:creator", "dc:date", "dc:coverage", "dc:description", "dc:identifier",
      "dc:rights", "dc:type", "dc:publisher", "dcterms:hasFormat"]
PUBLISHER = "Massey Herbarium, Virginia Tech (VPI)"


def to_dc(dwc, catalog_number, image_url, license_):
    """dwc: dict with the nine Darwin Core fields (values may be None). -> dict of Dublin Core elements."""
    v = {k: (dwc.get(k) or "").strip() for k in ("scientificName", "recordedBy", "recordNumber", "eventDate",
                                                  "country", "stateProvince", "county", "locality", "habitat")}
    ids = [f"collector-number:{v['recordNumber']}"] if v["recordNumber"] else []
    ids += [catalog_number] if catalog_number else []
    return {"dc:title": f"Herbarium specimen: {v['scientificName']}" if v["scientificName"] else "Herbarium specimen",
            "dc:subject": v["scientificName"], "dc:creator": v["recordedBy"], "dc:date": v["eventDate"],
            "dc:coverage": ", ".join(x for x in (v["country"], v["stateProvince"], v["county"], v["locality"]) if x),
            "dc:description": v["habitat"], "dc:identifier": " | ".join(ids),
            "dc:rights": license_, "dc:type": "PhysicalObject", "dc:publisher": PUBLISHER, "dcterms:hasFormat": image_url}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--source", required=True, choices=["model", "curated"])
    ap.add_argument("--model")
    ap.add_argument("--prompt")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = []
    for row in load_manifest(a.split):
        if a.source == "model":
            from run_model import load_cached
            dwc, err = load_cached(a.model, a.prompt, row["gbifID"])
            dwc = {} if err else dwc
        else:
            dwc = row
        out.append({"gbifID": row["gbifID"], "source": a.source if a.source == "curated" else a.model,
                    **to_dc(dwc, row["catalogNumber"], row["image_url"], row["license"])})
    write_csv(a.out, out, ["gbifID", "source"] + DC)
    print(f"wrote {a.out} ({len(out)} rows)")


if __name__ == "__main__":
    main()
