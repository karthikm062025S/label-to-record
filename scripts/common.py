"""Shared paths, field list, CSV and HTTP helpers. Stdlib only."""
import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
MANIFEST = DATA / "manifest.csv"

FIELDS = ["scientificName", "recordedBy", "recordNumber", "eventDate", "country",
          "stateProvince", "county", "locality", "habitat"]
SEED = 2026
UA = "herbarium-ai-audit/0.1 (student metadata research)"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_text(s):
    return sha256_bytes(s.encode("utf-8"))


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, columns):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_manifest(split=None):
    """Rows of the frozen manifest. Pass split='dev' or 'test' to read only that split."""
    rows = read_csv(MANIFEST)
    return [r for r in rows if split is None or r["split"] == split]


def http_get(url, headers=None, timeout=60, method="GET", retries=4):
    """-> (status, headers, body bytes). Retries 429/5xx and network errors with 2, 4, 8, 16 s backoff."""
    h = {"User-Agent": UA}
    h.update(headers or {})
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=h, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries:
                return e.code, dict(e.headers or {}), e.read() if e.fp else b""
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries:
                raise
        time.sleep(2 ** (attempt + 1))


def get_json_cached(url, cache_dir, headers=None):
    """GET a JSON URL once; the response is stored under cache_dir keyed by sha256(url)."""
    cache_dir = Path(cache_dir)
    path = cache_dir / (sha256_text(url) + ".json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]
    status, _, body = http_get(url, headers=headers)
    if status != 200:
        raise RuntimeError(f"HTTP {status} for {url}: {body[:300]!r}")
    data = json.loads(body.decode("utf-8"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"url": url, "fetched": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "response": data}, ensure_ascii=False), encoding="utf-8")
    return data


def qs(**params):
    return urllib.parse.urlencode(params)
