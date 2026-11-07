# Label to Record: can generative AI catalog Massey Herbarium specimens to Darwin Core, and where does it fail?

Status: plan, written before any model output exists (see PREREGISTRATION.md, committed first).
Author: Karthik Mandli. Date: 2026-11-06.

## 1. Question

Give a vision model nothing but the photograph of a Virginia Tech Massey Herbarium (VPI) specimen sheet. Ask it for nine Darwin Core terms. Compare what it writes to the curated GBIF record for the same sheet. Which fields can a library trust it to fill without a person checking, which fields need a person, and what kinds of mistakes does it make?

This is a small, honest version of the VT University Libraries "Metadata and AI Student Assistant" job: test an AI tool for metadata generation, measure accuracy, completeness and consistency against a reliable source and controlled vocabularies (Darwin Core, GBIF backbone, Getty TGN, LC Name Authority File, Dublin Core), refine the prompt, and write up a workflow a staff member can rerun.

Every number in REPORT.md must trace to a file in `results/`. No number is typed by hand.

## 2. What is already verified (probed 2026-11-06, no key needed)

- GBIF occurrence search, `institutionCode=VPI&country=US&stateProvince=Virginia&basisOfRecord=PRESERVED_SPECIMEN&mediaType=StillImage&kingdomKey=6`: 52,554 records. Adding `year=1700,2026`: 11,213 records (21%). The other 41,341 are skeletal: taxon, county and image, no collector, date or locality. That skeletal share is the "enhancement backlog" and will be reported as a finding, not sampled from (see 3.1 for why).
- Of 20 random dated records: recordedBy 19, locality 19, county 20, recordNumber 16, habitat 9, verbatimEventDate 1. So `eventDate` ground truth is the GBIF-interpreted ISO date, and `habitat` will be empty in the curated record about half the time.
- Year facet of the dated pool, by decade: 1930s 1,983; 1940s 1,094; 1950s 483; 1960s 2,011; 1970s 2,102; 1980s 1,315; 1990s 1,058; 2000s 424; 2010s 291; pre-1930 444; 2020s 8.
- Top collectors in the pool: R. Kral 705, A. B. Massey 591 (+ "A.B. Massey" 293), L.J. Uttal 470 (+ "L. J. Uttal" 273), Lena Artz 379, J. B. Lewis 301 (+ "J.B. Lewis" 273). The curated data itself spells one collector several ways. recordedBy scoring must normalize initials and spacing or it will punish the AI for the record's own inconsistency.
- License: 52,530 records CC BY 4.0, 24 CC BY-NC 4.0. Record `license` field carries it; the media entries carry `license: null`. Images are JPEGs on `media01.symbiota.org` (SERNEC portal). Example record fields seen: gbifID, catalogNumber (`VPI-V-0037794`), occurrenceID, scientificName (with authorship), acceptedScientificName, taxonKey, acceptedTaxonKey, family, recordedBy, recordNumber (`s.n.` for unnumbered), eventDate, year, country (`United States of America`), stateProvince, county, locality, habitat, license, datasetKey `b8499ea4-333e-495e-b419-34cb55db1408`, issues.
- Synonyms are real in the curated data: `Arabis lyrata L.` (taxonKey 5377106) has acceptedTaxonKey 3052468 (`Arabidopsis lyrata`). This is why name reconciliation is scored on the accepted key, not the string.
- GBIF species match: `https://api.gbif.org/v1/species/match?name=...` returns usageKey, acceptedUsageKey, matchType, confidence.
- LC Name Authority suggest: `https://id.loc.gov/authorities/names/suggest2?q=...` returns 200.
- Getty SPARQL: `https://vocab.getty.edu/sparql.json?query=...` (TGN is the place vocabulary). The TGN id for Virginia and the exact query shape are NOT yet verified; phase 4 probes them before any rate is computed.
- Gemini REST (`generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`), key in env `GEMINI_API_KEY`, images inline as base64, `responseMimeType: application/json`. Models available include gemini-2.5-flash, gemini-2.5-pro, gemini-3-flash-preview, gemini-3.1-pro-preview. No Gemini call is made before PREREGISTRATION.md is committed.

## 3. Design

### 3.1 Sample (phase 1, `scripts/sample.py`)

- Pool: the 11,213 dated VPI Virginia records (the query above with `year=1700,2026`). Reason: a record with no collector, date or locality cannot score those fields, and the study needs scorable ground truth. The cost of this choice is a selection bias: already-transcribed records may have more legible labels than the skeletal 79%. REPORT.md states this as limitation 1; the skeletal share is reported from the facet counts.
- Draw: `random.Random(2026)`, offsets sampled without replacement from `range(pool_count)`, fetched one record per offset (`limit=1&offset=k`). Oversample 160 draws, then accept in draw order with caps so the sample is spread: at most 8 per normalized collector string, at most 8 per family, at most 20 per decade. Stop at 100 accepted. Record every rejection and its reason in `data/sample_log.csv`.
- Accept only if: record has `recordedBy` and `eventDate`, has at least one `media` entry of type StillImage with a URL that answers HTTP 200 and `Content-Type: image/*` (HEAD, then GET on failure), and license is CC BY 4.0 or CC BY-NC 4.0 (record the value either way).
- Split: shuffle the 100 accepted gbifIDs with `random.Random(2026)`; first 30 are `dev`, remaining 70 are `test`.
- Output `data/manifest.csv` with columns: gbifID, catalogNumber, occurrenceID, split, image_url, license, family, year, and the curated fields scientificName, acceptedScientificName, taxonKey, acceptedTaxonKey, recordedBy, recordNumber, eventDate, verbatimEventDate, country, stateProvince, county, locality, habitat. The manifest is the frozen sample. GBIF result order can change over time, so a rerun of `sample.py` on another day may draw different records; the committed manifest is what later phases read, never a fresh draw.
- Images: `scripts/fetch_images.py` downloads each image once to `data/images/<gbifID>.jpg` (gitignored, they are large). If a file is over 7 MB, Pillow downscales the longest side to 3000 px into `data/images_small/`; the model gets the small one. Record which was sent per gbifID in `data/image_log.csv` (bytes, width, height, sha256).
- The test split is not opened by a human or a model until phase 5. The only pre-phase-5 action on test rows is the download and the HEAD check (so the frozen run cannot fail on a dead link).

### 3.2 Task and prompt

Input: one image, the prompt text, nothing else. Output: JSON with exactly these keys, string or null: scientificName, recordedBy, recordNumber, eventDate, country, stateProvince, county, locality, habitat. Enforced with Gemini `responseSchema`. `temperature: 0`.

Prompts live in `prompts/v1.txt` and `prompts/v2.txt`. v1 is a plain baseline: "Transcribe the specimen label into these Darwin Core fields; return null for anything not on the label." v2 is written after the dev error analysis and adds explicit rules (expected, but to be decided by the dev errors, not now): transcribe verbatim, do not expand abbreviations, null when not legible, eventDate as ISO 8601 with partial dates allowed (YYYY or YYYY-MM), never infer county or state from the locality or the herbarium name, scientificName is the name on the label or the most recent determination slip, authorship included if printed, collector names exactly as written. v2 is frozen by committing it and writing its sha256 into PREREGISTRATION.md (amendment section) before the test run; `scripts/run_model.py --split test` refuses to run if the prompt file hash differs from the frozen hash.

Leak audit (`tests/test_leak.py`, borrowed from the author's earlier research: the curated answer must never reach the prompt). The request builder takes only (image bytes, prompt text). The test serializes the exact request body for every manifest row and asserts that none of the curated field values (and none of their constituent words of 4+ letters, after the same normalization the scorer uses) appear anywhere in the body outside the base64 image blob, and that the body contains no catalogNumber, gbifID, image URL or filename. The audit runs in CI (the single `python -m pytest` or `python scripts/test_score.py` entry) and in `run_model.py` before each call.

### 3.3 Ground truth and the honesty caveat

Ground truth per field = the curated GBIF record value (interpreted field; verbatimEventDate is kept only to explain disagreements). The curated record can contain things that are not on the label: a later re-determination (different scientificName), a georeferencer's county, an editor's normalized collector name or expanded locality. So a disagreement is not automatically an AI error. Two layers handle that:

1. Automatic scoring classifies, but names the category honestly: "unsupported" (AI filled, record empty) instead of "hallucinated", because the automatic scorer cannot see the label.
2. A human image audit (phase 6) adjudicates a sample of disagreements and converts "unsupported" and "wrong" into "AI hallucinated", "record has non-label information", "both defensible" or "illegible".

### 3.4 Scoring (`scripts/score.py`, tests in `scripts/test_score.py`)

Per record and field, one category:

| Category | Meaning |
| --- | --- |
| exact | strings equal after whitespace collapse |
| normalized | equal after the field's normalization rule |
| partial | overlaps but not equal (rule per field below) |
| wrong | both have a value, no overlap |
| unsupported | AI filled, curated empty (upper bound on hallucination; audit decides) |
| omitted | AI null, curated has a value |
| both_empty | neither has a value (excluded from rates) |

Field normalization rules (pre-registered; the test file holds one example per rule):

- scientificName: strip authorship (everything after the second word, except infraspecific rank tokens `var.`, `subsp.`, `f.` and the epithet that follows), lowercase, collapse spaces. partial = genus matches only.
- recordedBy: lowercase, remove periods, collapse spaces, split on `,` `;` `&` ` and `, each part normalized to `initials surname` with single spaces; normalized = same set; partial = any shared surname.
- recordNumber: strip `no.`, `#`, `no`, spaces, lowercase; `s.n.`, `sn`, `s n` and null are all "unnumbered" and equal to each other (so AI null vs curated `s.n.` is normalized, not omitted).
- eventDate: parse to (year, month, day) with missing parts allowed; normalized = same parts present and equal (also `1936-5-3` = `1936-05-03`); partial = year equal and nothing contradicts (e.g. AI `1936` vs curated `1936-05-03`).
- country: one of `United States`, `United States of America`, `USA`, `U.S.A.`, `US`, `U.S.` are the same value.
- stateProvince: lowercase; `VA`, `Va.`, `Virginia` are the same.
- county: lowercase, strip trailing `county`, `co.`, `co`; normalized if equal.
- locality, habitat: lowercase, strip punctuation, collapse spaces; normalized if equal; partial if token Jaccard >= 0.5 or one string contains the other; else wrong.

Rates per field, computed on records where the curated value is present ("scorable", n_f):

- match = (exact + normalized) / n_f
- partial = partial / n_f
- wrong = wrong / n_f
- omitted = omitted / n_f
- unsupported = unsupported / (records where curated is empty)
- overall match = mean of per-field match across the nine fields (unweighted), reported beside the per-field table, never alone.

### 3.5 Confidence intervals (`scripts/stats.py`)

95% percentile bootstrap, 10,000 draws, seed 2026, ported from the author's earlier research code (`top1_ci`, `paired_bootstrap`) to stdlib `random` (no numpy). Clusters = normalized collector string, because sheets by one collector share one hand and one label style, so records are not independent; the cluster-resampled CI is the headline and the plain per-record CI is reported as secondary. The model comparison (strong minus fast) uses the paired bootstrap: the same resampled cluster indices applied to both models' per-record hit vectors before differencing; two-sided p is primary; the p-floor flag is kept.

### 3.6 Dev iteration (phase 3, dev split only, fast model)

1. Run v1 on the 30 dev records with the fast model. Score. Write `results/dev_v1_errors.md`: every non-match grouped by field and category, with the AI value and the curated value side by side.
2. Read the errors and write v2 rules that address the observed patterns, not imagined ones. One revision only (v1 to v2). If v2 is worse than v1 on dev overall match, keep v1 as the frozen prompt and say so.
3. Run v2 on dev with the fast model; score; compare. Dev numbers are reported in REPORT.md labeled "dev, used to write the prompt, not evidence".
4. Freeze: commit `prompts/v2.txt`, write its sha256 into PREREGISTRATION.md amendment A1.

### 3.7 Test run (phase 5, one run, two models)

One run of the frozen prompt on the 70 test records with two models: fast = gemini-2.5-flash, strong = gemini-3.1-pro-preview (first choice) or gemini-2.5-pro (fallback, chosen only if the 3.1 smoke call in phase 2 fails; the choice and the reason are logged in PREREGISTRATION.md amendment A2 before the test run). Raw responses cached under `results/raw/<sha256(model|prompt_sha|gbifID)>.json` with the full request metadata (minus the key) and the full response. A rerun reads the cache and makes zero calls. Test numbers go into REPORT.md whatever they are.

### 3.8 Reconciliation (phase 4 probe, phase 5 run; `scripts/reconcile.py`)

- scientificName -> GBIF backbone: `species/match?name=<AI name>`; record usageKey, acceptedUsageKey, matchType, confidence. Reconciled = the AI name's accepted key equals the curated acceptedTaxonKey. Reported with the string-match rate so the reader sees how many "wrong" strings are synonyms of the right taxon. Also apply to the curated scientificName itself as a control (it should reconcile to its own acceptedTaxonKey; any that do not are a data finding).
- county -> Getty TGN: phase 4 first probes the SPARQL endpoint to find the TGN id for Virginia (search by label "Virginia" with the United States as a broader parent) and confirms a query that returns a county by English label under that parent. Only then: match rate = share of distinct AI county strings (and, as a control, curated county strings) that resolve to exactly one TGN county under Virginia. If the probe cannot establish a working query in the phase 4 budget (20 requests), TGN is reported as "not reconciled, endpoint query not established" rather than guessed.
- recordedBy -> LC Name Authority File: `suggest2?q=<normalized name>&count=10`. Coverage = share of distinct collector strings with at least one suggestion whose label contains the surname and matches the initials after normalization. Expected low (field collectors are rarely in NAF). This is reported as a finding about vocabulary fit for herbarium collectors, not as an AI error.

### 3.9 Dublin Core crosswalk (`scripts/crosswalk.py`, `results/dublin_core.csv`)

| Darwin Core | Dublin Core (simple) | Note |
| --- | --- | --- |
| scientificName | dc:subject | also used to build dc:title: "Herbarium specimen: <scientificName>" |
| recordedBy | dc:creator | the collector made the specimen; a cultural-heritage profile might prefer dc:contributor; both options stated |
| recordNumber | dc:identifier | prefixed `collector-number:`; catalogNumber is a second dc:identifier |
| eventDate | dc:date | ISO 8601 |
| country, stateProvince, county, locality | dc:coverage | one spatial string, most specific last |
| habitat | dc:description | |
| (image URL) | dc:relation | the source image |
| (license) | dc:rights | from the GBIF record |
| (constant) | dc:type | `PhysicalObject` |
| (constant) | dc:publisher | `Massey Herbarium, Virginia Tech (VPI)` |
| (constant) | dc:format | `image/jpeg` for the surrogate |

Export: one row per test record from the strong model's v2 output, plus a second file from the curated values, so the two can be diffed.

### 3.10 Outputs

- REPORT.md: question, method, sample description (decades, collectors, families actually drawn), results tables with CIs, the error taxonomy with real examples (gbifID cited for each), image audit results, reconciliation results, the decision table from PREREGISTRATION.md filled in, recommended human-in-the-loop workflow, limitations.
- WORKFLOW.md: numbered steps a staff member follows to rerun on a new batch, with the exact commands and what each file means.
- results/: `manifest_stats.csv`, `dev_v1_scores.csv`, `dev_v2_scores.csv`, `test_<model>_scores.csv`, `test_summary.csv` (per field per model with CIs), `model_comparison.csv`, `reconcile_*.csv`, `audit_sample.csv`, `audit_results.csv`, `dublin_core.csv`, `raw/`.
- viewer.html: one self-contained page. Each test specimen image (loaded from its source URL at view time; not embedded) beside AI (both models) vs curated fields, cells colored by category; filters by field, category and model; counts update with the filter. Fonts embedded as base64 data URIs (Chrome blocks `@font-face url()` on file://), faces and palette from `design/SYSTEM.md`, loading, empty and error states (image failed to load shows the URL as a link), AA contrast, keyboard reachable filters, `prefers-reduced-motion` respected, calm dark mode via `prefers-color-scheme`. Proof: screenshots at 390 and 1440 px wide from the headless Chromium harness in `.claude/memory/headless-chromium-review-harness.md` (viewport set on `newContext`), looked at before the UI is called done.

## 4. Phases, gates and skills

| Phase | Work | Gate to pass | Skill / resource |
| --- | --- | --- | --- |
| 0 | PLAN.md + PREREGISTRATION.md, git init, commit | commit exists before any `results/raw/` file | a pre-committed outcome table, a falsifiable hypothesis with a kill condition |
| 1 | sample.py, fetch_images.py, manifest.csv, sample_log.csv | 100 rows, 30/70 split, every image file present, caps honored (checked by `test_score.py::test_manifest`) | stdlib only |
| 2 | prompt v1, run_model.py with cache + backoff + leak audit, score.py + test_score.py, stats.py, one smoke call per model on ONE dev record | tests green, leak test green, smoke responses parse, ~2 calls used | systematic debugging on any failure; security check: no key in any file or raw cache |
| 3 | dev v1 run, error analysis, v2, dev v2 run, freeze (amendment A1) | ~60 calls used, `prompts/v2.txt` sha in PREREGISTRATION.md | systematic debugging |
| 4 | reconcile.py probes: GBIF match, LC suggest, TGN query establishment; crosswalk.py | each endpoint returns a parsed result for one known input; TGN query found or declared not established | systematic debugging |
| 5 | test run, both models (140 calls), score, CIs, reconciliation on test, crosswalk export | `results/test_summary.csv` + `model_comparison.csv` exist, call count logged | none new |
| 6 | image audit sample (`audit_sample.csv`, up to 60 disagreements, stratified by field, seed 2026), the author adjudicates in `audit_results.csv` | every sampled row has a verdict | human step, the author's |
| 7 | REPORT.md, WORKFLOW.md, viewer.html + screenshots | every number in REPORT.md greps to a results file; screenshots looked at; fresh-context consistency review | fresh-context consistency review |

Budget: Gemini calls under 400 total (expected: 2 smoke + 60 dev + 140 test + retries). Backoff on 429 and 5xx: 2, 4, 8, 16, 32 s, then give up on that record and log it; a record that fails all retries is scored as `omitted` for every field and flagged `api_error` so the failure counts against the tool. Cache means a rerun costs zero calls.

## 5. Hypotheses (falsifiable, decided before data)

Written as falsifiable hypotheses (claim, kill condition, smallest test). The project-level pass and kill bars are in PREREGISTRATION.md; these are the scientific claims.

- H1 (field tiers). On test with the strong model: scientificName, country and stateProvince reach the auto-fill bar; recordedBy, eventDate, county reach at least the assist bar; locality and habitat do not reach auto-fill. Kill: any named auto-fill field falls below the assist bar, or locality reaches auto-fill. Either outcome is reported as is.
- H2 (prompt rules help). v2 lowers the dev sum of (wrong + unsupported) across fields versus v1 by at least 5 counts out of 30 records. Kill: v2 is not lower by 5; then v1 is the frozen prompt. Dev-only, exploratory, stated as such.
- H3 (model gap). Strong model overall match exceeds fast model by at least 5 points on test, paired cluster bootstrap CI excluding 0. Kill: CI includes 0; the report then says the fast model is the tool recommendation at this sample size and names the width of the CI as the detectable gap.
- H4 (synonyms hide inside "wrong"). At least half of the strong model's `wrong` scientificName values reconcile to the curated acceptedTaxonKey. Kill: fewer than half; then string mismatch is mostly a real transcription error.
- H5 (vocabulary fit). LC NAF coverage of the sample's collectors is below 50%; TGN resolves at least 90% of curated county strings. Kill for the second half: TGN below 90% or query not established; report either.
- H6 (non-label information). In the image audit, at least 20% of adjudicated disagreements are the record carrying information not on the label (re-determinations, georeferenced county, normalized names), not AI error. Kill: under 20%; then the curated record is a fair label transcription and the automatic rates stand as AI error rates.

Prior-art note (to write into REPORT.md, not re-derived here): published herbarium label OCR and vision-LLM transcription work exists; the report cites what it actually checks at phase 7 with full titles, never from memory.

## 6. What is deliberately not built

No fine-tuning, no OCR pre-pass, no multi-image prompts, no few-shot examples in the prompt (the label image is the only input, so the result is a zero-shot tool evaluation), no web app, no deploy, no GitHub push, no third model. Any of these is a follow-up, named in REPORT.md as such.

## 7. Repo layout

```
herbarium_ai_audit/
  PLAN.md  PREREGISTRATION.md  REPORT.md  WORKFLOW.md
  .gitignore            data/images/, data/images_small/, __pycache__
  prompts/v1.txt  prompts/v2.txt
  scripts/sample.py  fetch_images.py  run_model.py  score.py  test_score.py  test_leak.py
          stats.py  reconcile.py  crosswalk.py  build_viewer.py  audit_sample.py
  data/manifest.csv  sample_log.csv  image_log.csv
  results/*.csv  results/raw/*.json  results/dev_v1_errors.md
  viewer.html  screenshots/viewer_390.png  screenshots/viewer_1440.png
```

House rules: snake_case, stdlib first (Pillow only for the downscale), one test file for scoring and manifest checks, no em dashes, no hype words, the key never printed or written.

## 8. Paths as built (appended 2026-11-06; the text above is the pre-registered plan and is not edited)

| Planned path (above) | Real path |
| --- | --- |
| `scripts/test_score.py` | `tests/test_scoring.py` (run with `python -m unittest discover tests`) |
| `scripts/test_leak.py` | `tests/test_leak.py` |
| `results/dev_v1_errors.md` | `notes/dev_error_analysis.md` |
| `results/audit_results.csv` | not yet written; the author's adjudication. A reviewer's proposed verdicts for 40 of the 60 rows are in `results/audit_proposals.csv` (PREREGISTRATION.md A8) |
| `dc:relation`, `dc:format` in 3.9 | replaced by `dcterms:hasFormat` (image URL) so the specimen record describes one resource (PREREGISTRATION.md A7) |
| (not planned) | `scripts/common.py`, `compare_prompts.py`, `report_numbers.py`, `report_tables.py`, `viewer_template.html`; `notes/report_tables.md` |
