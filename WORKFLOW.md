# Workflow: rerun Label to Record on a new batch

For a staff member or student who wants to run the same audit on a new set of VPI records, or rerun this one. Every step is one command from the repo root. Python 3.12, stdlib only (Pillow only if an image is over 7 MB).

## 0. Setup

1. Set the Gemini key in the environment, never in a file: PowerShell `$env:GEMINI_API_KEY = "<key>"`, bash `export GEMINI_API_KEY=<key>`. The scripts send it as a header and never write it to disk.
2. Download the images: `python scripts/fetch_images.py`. Images are gitignored, so a fresh checkout has none, and the tests below read them. Rerunning this study: this downloads the 100 sheets in the committed `data/manifest.csv`. New batch: do step 1.1 first, then this.
3. Check the code: `python -m unittest discover tests`. This runs the scoring rules, the leak audit on every manifest row and prompt, and the manifest checks. All tests must pass before any model call.

## 1. Sample (skip 1.1 only when rerunning this study, because `data/manifest.csv` is the frozen sample; 1.2 always runs, as step 0.2)

1. `python scripts/sample.py --draws 400` draws records from GBIF (seed 2026, caps of 8 per collector, 8 per family and 20 per decade) and writes `data/manifest.csv`, `data/sample_log.csv` and `results/manifest_stats.csv`. A new draw on a later day can give different records, because GBIF's order changes; commit the manifest before any model call.
2. `python scripts/fetch_images.py` downloads each image once to `data/images/` (gitignored), downscales anything over 7 MB into `data/images_small/`, and writes `data/image_log.csv`.
3. Check the images by eye for the case this study missed: a record whose only image is a micrograph or a photo with no label (gbifID 5131791191 here). Drop or flag those before the run.

## 2. Prompt (dev split only)

1. Run the current prompt on dev: `python scripts/run_model.py --split dev --model gemini-3-flash-preview --prompt prompts/v2.txt`.
2. Score it: `python scripts/score.py --split dev --model gemini-3-flash-preview --prompt prompts/v2.txt --out results/dev_v2_scores.csv`.
3. Read every non-match in that file, grouped by field. Write any new rules into a new prompt file (`prompts/v3.txt`), with synthetic examples only. `python -m unittest tests.test_leak` fails if an example matches a record's own value.
4. Compare: `python scripts/compare_prompts.py results/dev_v2_scores.csv results/dev_v3_scores.csv --out results/dev_prompt_comparison_v3.csv`.
5. Freeze before test: commit the prompt, get its hash with `python -c "import sys; sys.path.insert(0, 'scripts'); from run_model import prompt_sha; print(prompt_sha('prompts/v3.txt'))"`, then append one line to section 7 of PREREGISTRATION.md that starts exactly `- A<next number> (prompt freeze` and contains `sha256 = <the 64-character hash>`, for example `- A9 (prompt freeze, 2026-12-01): prompts/v3.txt sha256 = 0123...`. Commit it. No code edit is needed: `run_model.py --split test` uses the hash in the last such line and refuses any prompt whose hash differs. The hash is taken from the text read with universal newlines, so a CRLF checkout gives the same hash.

## 3. Run (test split, once)

1. `python scripts/run_model.py --split test --model gemini-3-flash-preview --prompt prompts/v2.txt`
2. `python scripts/run_model.py --split test --model gemini-3.1-pro-preview --prompt prompts/v2.txt`

Both runs are required for steps 4 to 8 as written: `stats.py --comparison` needs two score files, and `report_numbers.py` and `build_viewer.py` name both models in code. With one model only: run `stats.py --scores <that file> --summary results/test_summary.csv` (no `--strong`, no `--comparison`), run `reconcile.py` and `crosswalk.py` on that model, and skip `report_numbers.py` and `build_viewer.py`.

Each response is cached in `results/raw/<sha256(model|prompt sha|gbifID)>.json`, so a rerun makes no calls. Calls back off on 429 and 5xx (2 to 32 s). A record that fails every retry is scored omitted on every field and flagged `api_error`. A 4xx such as "model not available" stops the run without caching and writes the error body to `results/raw_errors/`.

## 4. Score, intervals, comparison

```
python scripts/score.py --split test --model gemini-3-flash-preview --prompt prompts/v2.txt --out results/test_gemini-3-flash-preview_scores.csv
python scripts/score.py --split test --model gemini-3.1-pro-preview --prompt prompts/v2.txt --out results/test_gemini-3.1-pro-preview_scores.csv
python scripts/stats.py --scores results/test_gemini-3-flash-preview_scores.csv results/test_gemini-3.1-pro-preview_scores.csv --strong gemini-3.1-pro-preview --summary results/test_summary.csv --comparison results/model_comparison.csv
```

All commands run from the repo root. Prompt paths are read relative to the repo root; `--out` paths are relative to where you run the command.

What the files mean:
- `results/test_<model>_scores.csv`: one row per record and field: AI value, catalog value, category (exact, normalized, partial, wrong, unsupported, omitted, both_empty), collector cluster.
- `results/test_summary.csv`: per field and model: rates, 95% CIs clustered by collector, per-record CIs, and the tier from the pre-registered rules (auto_fill, assist, do_not_use).
- `results/model_comparison.csv`: strong minus fast overall match, paired cluster bootstrap CI and p.

## 5. Reconcile and export

```
python scripts/reconcile.py --scores results/test_gemini-3.1-pro-preview_scores.csv
python scripts/crosswalk.py --split test --source model --model gemini-3.1-pro-preview --prompt prompts/v2.txt --out results/dublin_core.csv
python scripts/crosswalk.py --split test --source curated --out results/dublin_core_curated.csv
python scripts/report_numbers.py --out results/report_numbers.csv
python scripts/report_tables.py
```

- `reconcile_gbif_*.csv`: each AI and catalog name matched to the GBIF backbone; `ai_reconciled = 1` when the AI name's accepted key equals the catalog's acceptedTaxonKey.
- `reconcile_tgn_*.csv`: each distinct county string against Getty TGN counties under Virginia (tgn:7007919). Independent cities do not resolve; keep a local list of them.
- `reconcile_lcnaf_*.csv`: each collector against the LC Name Authority File suggest2 service. A hit with the same initials and surname is only plausible, not confirmed.
- `dublin_core*.csv`: simple Dublin Core, one row per record, from the AI output and from the catalog, for diffing.

## 6. Human audit (the step that makes auto-fill possible)

1. `python scripts/audit_sample.py results/test_gemini-3-flash-preview_scores.csv results/test_gemini-3.1-pro-preview_scores.csv --out results/audit_sample.csv` draws up to 60 wrong or unsupported rows, stratified by field (seed 2026).
2. Copy it to `results/audit_results.csv`. For each row, open `image_url` and fill `verdict` with one of: `ai_wrong`, `record_has_non_label_info`, `both_defensible`, `illegible`. Add a note when it helps.
3. Rerun `scripts/stats.py` (step 4). The tier column now uses the audited hallucination rate, and a field can reach auto_fill.
4. Only after step 2 is done, compare your verdicts with a second reader's, if there is one (for this study, `results/audit_proposals.csv` holds a reviewer's proposed verdicts for 40 of the 60 rows). Report the agreement rate. Reading the other file first would make your audit non-independent.

## 7. How to use the output in cataloging (current recommendation)

Based on the 2026-11-06 test run (see `PREREGISTRATION.md` section 8 for the numbers):

| Field | What to do with the AI value |
| --- | --- |
| eventDate, stateProvince, country | Pre-fill; a person confirms. Candidates for auto-fill once the audit is in. |
| recordNumber | Pre-fill; a person checks every value, and especially nulls (the strong model omitted 15%). |
| scientificName | Reconcile to the GBIF backbone. Accept when the accepted key matches the expected taxon; send the rest (6 of 69 here) to a person. |
| recordedBy | Draft only; a person corrects. Match to a local collector authority, not LCNAF alone (plausible hit for 37.5% of collector strings when any one person counts, 34.9% of real persons; corrected 2026-11-07). |
| county | Draft only; a person corrects. Resolve to TGN plus a local list of Virginia independent cities. |
| locality, habitat | Draft only. The prompt's habitat rule needs a fix with fresh dev data before these are worth pre-filling. |

Model: use gemini-3-flash-preview by default. Use gemini-3.1-pro-preview as a second pass on fields the fast model left null or a person flagged. The stronger model was not better overall on this sample (+0.6 points, CI -0.9 to +2.1).

## 8. View the results

`python scripts/build_viewer.py`, then open `viewer.html` in a browser. It shows each test sheet (loaded from its source URL) beside the catalog values and both models' values, colored by category, with filters for model, field and category. Fonts: the committed page embeds two open-licence faces; rebuilding it uses system fonts.
