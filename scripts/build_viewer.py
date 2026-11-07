"""Build viewer.html: every test specimen beside the curated record and both models' v2 output (PLAN.md 3.10).

  python scripts/build_viewer.py

Reads data/manifest.csv (test rows), data/image_log.csv (image size), results/test_<model>_scores.csv and
results/test_summary.csv. Images load from their source URL at view time; nothing is embedded but the data.

Fonts: the page uses the system fonts. (The committed viewer.html also embeds two open-licence faces,
Instrument Serif and Departure Mono; rebuilding does not re-embed them.)
"""
import html
import json
from pathlib import Path

from common import DATA, FIELDS, RESULTS, ROOT, load_manifest, read_csv

MODELS = [("gemini-3-flash-preview", "Fast"), ("gemini-3.1-pro-preview", "Strong")]


def data():
    sizes = {r["gbifID"]: (r["width"], r["height"]) for r in read_csv(DATA / "image_log.csv")}
    scores = {}
    for model, _ in MODELS:
        for r in read_csv(RESULTS / f"test_{model}_scores.csv"):
            scores[(r["gbifID"], model, r["field"])] = (r["ai_value"], r["category"])
    recs = []
    for row in load_manifest("test"):
        g = row["gbifID"]
        w, h = sizes[g]
        recs.append({"id": g, "cat": row["catalogNumber"], "url": row["image_url"], "w": int(w), "h": int(h),
                     "family": row["family"], "year": row["year"], "license": row["license"],
                     "fields": [{"f": f, "cur": row[f], **{m: list(scores[(g, m, f)]) for m, _ in MODELS}}
                                for f in FIELDS]})
    summary = [r for r in read_csv(RESULTS / "test_summary.csv")]
    return {"models": [{"id": m, "label": lab} for m, lab in MODELS], "fields": FIELDS, "records": recs,
            "summary": summary}


def main():
    payload = json.dumps(data(), ensure_ascii=False).replace("</", "<\\/")
    page = (ROOT / "scripts" / "viewer_template.html").read_text(encoding="utf-8")
    page = page.replace("/*EMBEDDED_FONTS*/", "").replace("__DATA__", payload)
    (ROOT / "viewer.html").write_text(page, encoding="utf-8")
    print(f"wrote viewer.html ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
