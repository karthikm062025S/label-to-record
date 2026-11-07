"""Gemini extraction client: one image + the prompt text in, nine Darwin Core fields out (PLAN.md 3.2, 3.7).

  python scripts/run_model.py --split dev --model gemini-2.5-flash --prompt prompts/v1.txt [--ids 123,456]

- The key is read from the GEMINI_API_KEY environment variable and sent as a header. It is never printed,
  never written to disk, and the cached request metadata does not contain it.
- Cache: results/raw/<sha256(model|prompt_sha|gbifID)>.json holds the request metadata and the full response.
  A cached record makes zero calls, so a rerun is free.
- Backoff on 429 and 5xx: 2, 4, 8, 16, 32 s, then the record is logged as api_error and scored omitted.
- Leak audit before every call (leak_findings): the request text must be identical for every record and must
  not contain any curated value or identifier of the record. Any finding stops the run.
- --split test refuses to run unless the prompt's sha256 equals the one in the LAST PREREGISTRATION.md amendment
  line that starts '- A<n> (prompt freeze' and contains 'sha256 = <64 hex>' (A1 for this study's v2 prompt).
- A non-retryable 4xx stops the run uncached; its status and error body (no key) go to results/raw_errors/.
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from common import FIELDS, RESULTS, ROOT, load_manifest, sha256_bytes, sha256_text
from fetch_images import image_for
from score import norm_text

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RAW = RESULTS / "raw"
BACKOFF = [2, 4, 8, 16, 32]
SCHEMA = {"type": "OBJECT", "properties": {f: {"type": "STRING", "nullable": True} for f in FIELDS},
          "required": FIELDS, "propertyOrdering": FIELDS}
IMAGE_PLACEHOLDER = "<image bytes omitted>"
# Words of the Darwin Core field names. A curated value may contain one of these ("Montgomery County") and the
# schema necessarily contains it, so these are the only curated words allowed in the request text.
FIELD_WORDS = {"scientific", "name", "recorded", "record", "number", "event", "date", "country", "state",
               "province", "county", "locality", "habitat"}


def prompt_sha(prompt_path):
    return sha256_text((ROOT / prompt_path).read_text(encoding="utf-8"))


def build_request(image_bytes, prompt_text):
    """The request body. Takes only the image and the prompt: no curated field can reach it by construction."""
    return {"contents": [{"role": "user", "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}},
                {"text": prompt_text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": SCHEMA}}


def request_text(body):
    """The serialized body with the base64 image replaced by a placeholder: everything the model reads as text."""
    b = json.loads(json.dumps(body))
    for part in b["contents"][0]["parts"]:
        if "inline_data" in part:
            part["inline_data"]["data"] = IMAGE_PLACEHOLDER
    return json.dumps(b, ensure_ascii=False, sort_keys=True)


def leak_findings(text, row):
    """Own-record leak check (the rule from the author's earlier leak audit: check a record against ITS OWN
    answer, normalized the way the scorer normalizes). Returns a list of findings; empty means clean."""
    norm = " " + norm_text(text.replace("_", " ")) + " "
    found = []
    for key in ("gbifID", "catalogNumber", "occurrenceID", "image_url"):
        if row.get(key) and row[key] in text:
            found.append((key, "identifier"))
    stem = row["image_url"].rsplit("/", 1)[-1].rsplit(".", 1)[0] if row.get("image_url") else ""
    if stem and stem.lower() in text.lower():
        found.append(("image_url", "file name"))
    for f in FIELDS + ["acceptedScientificName"]:
        value = norm_text(row.get(f, ""))
        if len(value) >= 4 and f" {value} " in norm:
            found.append((f, "full value"))
        for word in set(value.split()):
            if len(word) >= 4 and word.isalpha() and word not in FIELD_WORDS and f" {word} " in norm:
                found.append((f, f"word '{word}'"))
    return found


def cache_path(model, prompt_path, gbif_id):
    return RAW / f"{sha256_text(f'{model}|{prompt_sha(prompt_path)}|{gbif_id}')}.json"


def parse_response(resp):
    """-> (dict of the nine fields, error string or None)."""
    try:
        text = "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"] if not p.get("thought"))
        data = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
        return None, f"unparseable response: {type(e).__name__}"
    if not isinstance(data, dict):
        return None, "response JSON is not an object"
    return {f: data.get(f) for f in FIELDS}, None


def load_cached(model, prompt_path, gbif_id):
    """-> (prediction dict or None, error or None). A missing cache file is an error: the record was not run."""
    p = cache_path(model, prompt_path, gbif_id)
    if not p.exists():
        return None, "not run"
    rec = json.loads(p.read_text(encoding="utf-8"))
    return rec.get("parsed"), rec.get("error")


def call(model, body, key):
    """POST with backoff. -> (http status, response dict or None, attempts, latency seconds of the last try)."""
    data = json.dumps(body).encode()
    for attempt, wait in enumerate(BACKOFF + [None], start=1):
        req = urllib.request.Request(API.format(model=model), data=data, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.status, json.loads(r.read()), attempt, time.time() - t0
        except urllib.error.HTTPError as e:
            status, payload = e.code, e.read()[:2000].decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            status, payload = 0, repr(e)[:500]
        if status not in (0, 429, 500, 502, 503, 504) or wait is None:
            return status, {"error_body": payload}, attempt, time.time() - t0
        print(f"  HTTP {status}, retry in {wait}s", flush=True)
        time.sleep(wait)


def frozen_sha():
    """sha256 in the last '- A<n> (prompt freeze' amendment line of PREREGISTRATION.md, or None if there is none."""
    hits = re.findall(r"^- A\d+ \(prompt freeze[^\n]*?sha256 = ([0-9a-f]{64})",
                      (ROOT / "PREREGISTRATION.md").read_text(encoding="utf-8"), re.M)
    return hits[-1] if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", required=True, help="path relative to the repo root, e.g. prompts/v1.txt")
    ap.add_argument("--ids", help="comma-separated gbifIDs within the split (for a smoke call)")
    a = ap.parse_args()
    psha = prompt_sha(a.prompt)
    if a.split == "test" and psha != frozen_sha():
        sys.exit(f"refusing --split test: {a.prompt} sha256 {psha} is not the frozen hash ({frozen_sha()})")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY is not set")
    prompt_text = (ROOT / a.prompt).read_text(encoding="utf-8")
    rows = load_manifest(a.split)  # only this split's rows are loaded
    if a.ids:
        want = set(a.ids.split(","))
        rows = [r for r in rows if r["gbifID"] in want]
        if len(rows) != len(want):
            sys.exit("some --ids are not in this split")
    RAW.mkdir(parents=True, exist_ok=True)
    texts, calls, errors = set(), 0, 0
    for row in rows:
        path = cache_path(a.model, a.prompt, row["gbifID"])
        if path.exists():
            continue
        img_path = image_for(row["gbifID"])
        img = img_path.read_bytes()
        body = build_request(img, prompt_text)
        text = request_text(body)
        texts.add(text)
        leaks = leak_findings(text, row)
        if leaks or len(texts) > 1:
            sys.exit(f"leak audit failed for {row['gbifID']}: {leaks or 'request text differs between records'}")
        status, resp, attempts, latency = call(a.model, body, key)
        calls += attempts
        if status not in (200, 0, 429, 500, 502, 503, 504):
            # A 4xx such as 404 'model not available' is a configuration error, not a per-record failure:
            # stop without caching, so it is never scored as an api_error omission. The error body (no key: the
            # key travels in a header) is kept in results/raw_errors/ so a claim about it traces to a file.
            err_dir = RESULTS / "raw_errors"
            err_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y-%m-%dT%H-%M-%S")
            (err_dir / f"{a.model}_{stamp}.json").write_text(json.dumps(
                {"model": a.model, "gbifID": row["gbifID"], "http_status": status, "created": stamp,
                 "error_body": resp.get("error_body", "")}, ensure_ascii=False, indent=1), encoding="utf-8")
            sys.exit(f"HTTP {status} on {row['gbifID']}, not cached, run stopped: {resp.get('error_body', '')[:500]}")
        parsed, err = parse_response(resp) if status == 200 else (None, f"api_error HTTP {status}")
        errors += bool(err)
        record = {"model": a.model, "prompt": a.prompt, "prompt_sha256": psha, "gbifID": row["gbifID"],
                  "split": a.split, "image_file": img_path.relative_to(ROOT).as_posix(),
                  "image_sha256": sha256_bytes(img), "image_bytes": len(img), "request_text": text,
                  "http_status": status, "attempts": attempts, "latency_s": round(latency, 2),
                  "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "response": resp, "parsed": parsed, "error": err}
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        usage = (resp or {}).get("usageMetadata", {})
        print(f"{row['gbifID']}: HTTP {status} in {latency:.1f}s, tokens in/out "
              f"{usage.get('promptTokenCount')}/{usage.get('candidatesTokenCount')}, error={err}", flush=True)
    print(f"{len(rows)} records, {calls} HTTP calls made, {errors} errors")


if __name__ == "__main__":
    main()
