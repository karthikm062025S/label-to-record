# Pre-registration: Label to Record

Committed before any model output exists. The git commit timestamp on this file is the proof. Nothing in sections 1 to 6 changes after the first Gemini call; later changes go only into section 7 (amendments), dated, with the reason.

Author: Karthik Mandli. Date: 2026-11-06. Companion: PLAN.md (method detail).

## 1. Question

For each of nine Darwin Core fields, can a vision model reading only the specimen sheet image fill the field well enough that a library would (a) auto-fill it, (b) pre-fill it for human verification, or (c) not use it? Decided on the 70-record test split with the frozen prompt, per model.

## 2. Gate: field trust tiers

| Field | Value |
| --- | --- |
| 1. Question | Per Darwin Core field and per model: auto-fill, assist, or do not use? |
| 2. Metric + measurement | match = (exact + normalized) / scorable records; wrong = wrong / scorable; omitted = omitted / scorable; unsupported = unsupported / records with empty curated value; hallucination (audited) = share of audited "unsupported" and "wrong" rows where the adjudicator sees no support on the label. Source: `results/test_<model>_scores.csv` produced by `scripts/score.py` on `data/manifest.csv` rows with `split == test` (n = 70 records; scorable n per field reported in `results/test_summary.csv`). CIs: 95% percentile bootstrap, 10,000 draws, seed 2026, clustered by normalized collector (`scripts/stats.py`). Audit source: `results/audit_results.csv`. |
| 3. Pass bar (auto-fill) | match >= 95% AND wrong <= 1% AND audited hallucination <= 1% for that field. At n = 70 scorable, wrong <= 1% means zero wrong rows. Decision: the field is listed as "safe to auto-fill with spot checks" in REPORT.md and WORKFLOW.md. |
| 4. Kill bar (do not use) | match < 80% OR wrong > 5% OR omitted > 50%. Decision: the field is listed as "do not use the AI value; human transcribes", and the error examples for that field go in the taxonomy section. |
| 5. Gray zone (assist) | Everything between: match in [80%, 95%) or wrong in (1%, 5%] or audited hallucination in (1%, 5%]. Decision: "AI pre-fills, human verifies every value". Tiebreaker when a field sits within 2 points of a bar: the image audit is extended to every disagreement for that field (not a sample); if at least half of those disagreements are the record carrying non-label information, the field is reported in the higher tier with that reason written next to it; otherwise it stays in the lower tier. The tiebreaker is one bounded audit, never a rerun of the model. |
| 6. Stall trigger | The image audit (phase 6) is the chore next to the comfortable substitute (more scoring). Deadline: 2026-11-11. If `results/audit_results.csv` does not exist by then, every hallucination number in REPORT.md is labeled "auto-scored upper bound, unaudited", no field is placed in the auto-fill tier (because bar 3 needs the audit), and H6 is reported as not tested. |
| 7. Hard stop | 2026-11-13. If the frozen test run (`results/test_summary.csv`) does not exist by then, the default decision fires: REPORT.md ships with dev-only numbers labeled "dev, used to write the prompt, not evidence", and APPLICATION_NOTES.md makes no accuracy claim beyond "built the harness and the pre-registered protocol". No extension. |
| 8. Gate cost budget | Under 400 Gemini calls total (expected about 200). About two working days of the author's attention plus one audit block (about 60 adjudications, under 2 hours). Not built during the gate: OCR pre-pass, few-shot prompts, a third model, a web app, deploy, GitHub repo, any fine-tuning. |

### Tier rules restated as code (what `scripts/score.py --tiers` applies)

```
if match >= 0.95 and wrong <= 0.01 and audited_halluc <= 0.01: tier = "auto_fill"
elif match < 0.80 or wrong > 0.05 or omitted > 0.50:            tier = "do_not_use"
else:                                                           tier = "assist"
# audited_halluc is None (audit missing) -> auto_fill is impossible; the row says "audit missing".
```

The strong model's tiers are the headline. The fast model's tiers are reported beside them. If the two models disagree on a field's tier, the report says so; it does not pick the better one.

## 3. Gate: model comparison

| Field | Value |
| --- | --- |
| 1. Question | Is the stronger model worth its cost for this task? |
| 2. Metric + measurement | overall match (unweighted mean of the nine per-field match rates) per model on test; gap = strong minus fast; paired cluster bootstrap (same resample applied to both), 10,000 draws, seed 2026, two-sided p primary. Source: `results/model_comparison.csv`. Also: wrong + unsupported counts per model, and per-record latency and token counts from the raw cache (`results/raw/*.json`). |
| 3. Pass bar | gap >= 5 points AND 95% CI excludes 0. Decision: WORKFLOW.md recommends the strong model. |
| 4. Kill bar | gap <= 0 with CI excluding 0 (fast model better). Decision: WORKFLOW.md recommends the fast model and the report names this as a finding. |
| 5. Gray zone | gap between 0 and 5, or CI includes 0. Decision: WORKFLOW.md recommends the fast model as default with the strong model as the second pass on fields the fast model left null or the human flagged; the report states the CI width as the smallest gap this sample could have detected. No rerun. |
| 6. Stall trigger | Same as gate 2 field 6 (the audit) for the hallucination column; the comparison itself has no stall step because it is produced by the same script run. |
| 7. Hard stop | 2026-11-13, same default as gate 2. |
| 8. Gate cost budget | 140 of the 400 calls. |

## 4. Gate: reconciliation and vocabulary fit

| Field | Value |
| --- | --- |
| 1. Question | Do the AI's names and places resolve to the same controlled-vocabulary entries as the curated record, and do the vocabularies cover this collection at all? |
| 2. Metric + measurement | GBIF backbone: share of strong-model scientificName values whose accepted usage key equals the curated acceptedTaxonKey (`results/reconcile_gbif.csv`), plus the same for curated names as a control. Getty TGN: share of distinct county strings (AI and curated, separately) that resolve to exactly one TGN place under Virginia (`results/reconcile_tgn.csv`). LC NAF: share of distinct collector strings with a plausible suggest2 hit (`results/reconcile_lcnaf.csv`). |
| 3. Pass bar | GBIF: AI accepted-key agreement >= 90% on records where scientificName was not omitted. Decision: name reconciliation goes into WORKFLOW.md as an automatic step. TGN: curated county resolution >= 90%. Decision: TGN is recommended as the place authority for county. |
| 4. Kill bar | GBIF agreement < 75%. Decision: names are human-verified before reconciliation. TGN < 60% or query not established within 20 probe requests. Decision: TGN is reported as "not fit or not established" and the report proposes the GBIF GADM county field or a local county list instead. |
| 5. Gray zone | GBIF 75% to 90%: reconciliation runs automatically but every non-match is routed to the human queue (reported as the queue size). TGN 60% to 90%: TGN used with a local fallback list; the unmatched strings listed. LC NAF has no bar; its coverage number is a finding in itself (expected under 50%, H5). |
| 6. Stall trigger | The TGN probe (SPARQL query shaping) is the step most likely to be skipped. Deadline 2026-11-10; if no working query by then, the kill-bar decision fires for TGN. |
| 7. Hard stop | 2026-11-13. |
| 8. Gate cost budget | Under 300 vocabulary requests across the three services; no API keys. |

## 5. Claims the gates stand on

- certain: VPI = Massey Herbarium records are on GBIF with images under CC BY 4.0 (facet counts probed 2026-11-06, PLAN.md section 2).
- certain: 11,213 dated records exist and dated records mostly carry collector and locality (20-record probe, 19/20 each).
- certain: GBIF match, LC suggest2 and Gemini REST respond as described (probed 2026-11-06).
- probable: the curated GBIF record is a fair transcription of the label for most fields. Basis: SERNEC portal records are keyed from the sheet; counter-evidence: re-determinations and georeferencing exist by design. This claim is what H6 and the image audit measure, so the gate does not stand on it blindly; if it is false, the automatic "wrong" rate overstates AI error, which is why bar 3 requires the audit.
- assumed: the image resolution on media01.symbiota.org is high enough to read handwriting. If false, omitted rates will be high for every model and the report says the images, not the model, are the limit. This claim is measured by the omitted column, not assumed by the bars. Check: "if this is false, does the pass bar still mean anything?" Yes: a field that fails because of image quality still fails the library's purpose, so the tiers stay valid as a verdict on the tool-plus-images pipeline, and the report attributes the cause.
- assumed: Gemini 3.1 pro preview is callable with this key. If false, the fallback model is pre-named (gemini-2.5-pro) and logged in amendment A2 before the test run.

## 6. Things fixed now so they cannot drift

- Sample seed 2026; split seed 2026; bootstrap seed 2026; 10,000 draws.
- Caps: 8 per collector, 8 per family, 20 per decade; 160 oversample; 100 accepted; 30 dev, 70 test.
- Fields: scientificName, recordedBy, recordNumber, eventDate, country, stateProvince, county, locality, habitat.
- Categories: exact, normalized, partial, wrong, unsupported, omitted, both_empty. Normalization rules per field as in PLAN.md section 3.4; the locality and habitat partial threshold is token Jaccard >= 0.5.
- Prompt iterations: exactly one revision on dev (v1 to v2); v2 frozen by hash before test.
- Models: fast = gemini-2.5-flash; strong = gemini-3.1-pro-preview, fallback gemini-2.5-pro. temperature 0, JSON schema output.
- Test split rows are not read by any person or model until phase 5. A dev script that reads a test row is a protocol breach and is logged as such.
- Leak audit: curated values never enter the request body; `scripts/test_leak.py` must pass before each run.
- Audit sample: up to 60 disagreement rows, stratified by field, seed 2026, adjudicated by the author (not a botanist; stated as a limitation), four verdicts: ai_wrong, record_has_non_label_info, both_defensible, illegible.
- Every REPORT.md number comes from a `results/` file; no hand-typed numbers.
- Multiple honest variants of a headline are reported together (per-field table, overall mean, clustered and unclustered CI), never only the most flattering one.

## 7. Amendments (dated, appended only, never edited above)

- A1 (prompt freeze, filled 2026-11-06 at the end of phase 3, before any test call): `prompts/v2.txt` sha256 = 6263d380a0bdbbced553d5ff85279c97a304dbd2cd06ad88bf35ba28667856c0 ; dev overall match v1 = 0.608 , v2 = 0.751 (gap +0.143, paired cluster bootstrap 95% CI 0.081 to 0.201; `results/dev_prompt_comparison.csv`) ; frozen prompt = v2. H2 (dev, exploratory): wrong + unsupported fell from 64 to 21, so the kill condition (a drop under 5) did not fire. Model used on dev: gemini-3-flash-preview (the fast model per A2). Known v2 costs seen on dev and left in place, because only one revision is allowed: habitat match fell from 0.778 to 0.222 (7 of 9 curated habitats now null), and scientificName match fell from 0.733 to 0.633 (infraspecific ranks added from slips, abbreviated genus on two determination slips). Error analysis: `notes/dev_error_analysis.md`.
- A2 (model availability, filled at phase 2 smoke, 2026-11-06): strong model = gemini-3.1-pro-preview ; reason = the first choice answered the smoke call (HTTP 200, parsed JSON, dev gbifID 3893483883). The pre-named fast model and the pre-named fallback both fail for this key with HTTP 404, verbatim: "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash ..." and the same message for models/gemini-2.5-pro. Both are still listed by the models endpoint, so listing is not availability. Change: fast model = gemini-3-flash-preview (HTTP 200 on the same smoke record), chosen over gemini-3.8-flash because it is the same generation as the strong model, which keeps "fast versus strong" a size comparison rather than a generation comparison. Consequence: there is no working fallback if gemini-3.1-pro-preview is withdrawn before the test run; if that happens, the test run uses gemini-3.8-flash as the second model and the comparison is relabeled "two fast models", logged here first.
- A3 (oversample size, 2026-11-06, before any Gemini call). The 160-draw oversample in section 6 accepted only 74 records: 79 of the 86 rejections included the family cap (72 of them Asteraceae; first 160 rows of `data/sample_log.csv`), because Asteraceae is 6,322 of the 11,213 dated pool records (56%, GBIF familyKey facet, probed 2026-11-06). Change: the draw continues in the same seeded sequence until 100 are accepted, with a ceiling of 400 draws (`scripts/sample.py --draws 400`). `random.Random(2026).sample(range(11213), k)` is prefix-stable (the first 160 of 400 equal the 160-draw, checked), so the first 160 accept/reject decisions are unchanged (74 accepted in both). Caps, 100 accepted, the 30/70 split and the split seed are unchanged. Result: 274 draws used (`results/manifest_stats.csv`). Consequence for REPORT.md: the sample deliberately under-represents Asteraceae relative to the pool (8 of 100 vs 56%), which the family cap was designed to do; this is stated beside limitation 1.
- A4 (scorer gap, found 2026-11-06 after the test run, scorer NOT changed). `scripts/score.py` compares the scientificName genus byte-wise (`ai.split()[0].lower()`), so a diacritic the label prints scores "wrong", not "normalized" or "partial". Test cases: 3893447816 and 3893461253 (AI `Isoëtes`, catalog `Isoetes`), both models. Changing the scorer now would change test numbers after they were seen, so the registered scorer stands and the gap is reported in REPORT.md. First item for a v3 scorer: Unicode NFKD and strip combining marks before every comparison.
- A5 (timing record, 2026-11-06, no rerun). The two smoke calls and the dev v1 run began at 21:19:45 (raw cache `created` field), before the harness commit bc453ed at 21:21:20, so the leak-audit code that guarded the first dev v1 calls is not provably the committed version. Dev only. Every test call (first 21:41:01, last 21:58:29) ran after the harness commit and after the prompt-freeze commit 004bb72 (21:40:40); all 140 test raw files first appear in commit 2893bb1.
- A6 (paths as built, 2026-11-06). Section 6 names `scripts/test_leak.py`; the file is `tests/test_leak.py`, and the scoring tests are `tests/test_scoring.py` (PLAN.md says `scripts/test_score.py`). The dev error write-up is `notes/dev_error_analysis.md` (PLAN.md: `results/dev_v1_errors.md`). Section 6 is left as written; PLAN.md has a "Paths as built" note at the end.
- A7 (code changes after the test run that do not change any result, 2026-11-06). (a) `run_model.py` reads the frozen hash from the last amendment line starting `- A<n> (prompt freeze`, so a new prompt is frozen by appending an amendment, not by editing code; for v2 it still returns the A1 hash (checked). (b) A non-retryable 4xx now writes its status and error body (never the key, which travels in a header) to `results/raw_errors/`. The A2 claim about HTTP 404 predates this and has no file; its verbatim quote above is the record, and the same 404 message was reproduced live on 2026-11-06 by an independent reviewer. (c) `crosswalk.py` no longer puts `dc:format image/jpeg` and `dc:relation` on the specimen record (DCMI one-to-one); the image URL is `dcterms:hasFormat`. (d) viewer focus ring colour and licence legend. (e) `report_numbers.py` defines "AI-filled" in the row name and adds a post-hoc LC NAF row (every person in the string has a hit). `results/test_summary.csv` and `results/model_comparison.csv` are unchanged.
- A8 (audit seed, 2026-11-06). A second Claude Code agent, acting as independent reviewer, read the label image for 40 of the 60 rows in `results/audit_sample.csv` and wrote proposed verdicts to `results/audit_proposals.csv`. That file is not `results/audit_results.csv`, `stats.py` does not read it, and it changes no tier: Karthik is the pre-registered adjudicator and confirms or overrides each row. The four registered verdicts have no category for "the label supports the AI and the catalog is empty or mistyped"; the proposals use `both_defensible` with a note for those. Adding a fifth verdict is Karthik's call and must be made, as an amendment, before he reads his own audit totals. To keep his audit independent, the recommended order is: fill `results/audit_results.csv` from `results/audit_sample.csv` without opening the proposals, then compare the two files and report the agreement rate as a two-rater check. REPORT.md discusses some of these rows by name, so the audit is not fully blind for those rows; this is stated as a limitation.

## 8. Result (filled after the run, against the tables above, verdicts direct)

Filled 2026-11-06, after the one frozen test run (prompt v2, 70 records, both models, 140 calls, 0 errors; `results/run_log_test_v2_flash.txt`, `results/run_log_test_v2_pro.txt`). The image audit (`results/audit_results.csv`) does not exist yet, so the gate 2 stall rule applies until 2026-11-11: hallucination numbers are auto-scored upper bounds, unaudited, and no field is placed in auto_fill. `results/audit_sample.csv` (60 of the 62 wrong or unsupported test rows, both models) is drawn and waiting for Karthik's verdicts.

Gate 2 per field (strong model is the headline; fast model in brackets; source `results/test_summary.csv`):
- scientificName: match 72.9% [72.9%] -> do_not_use [do_not_use].
- recordedBy: match 72.9% [74.3%] -> do_not_use [do_not_use].
- recordNumber: match 83.0% [86.8%], wrong 1.9% [3.8%] -> assist [assist].
- eventDate: match 97.1%, wrong 1.4% (one row) [same] -> assist [assist]. Tiebreaker due: wrong sits 0.4 points above the 1% bar, so every eventDate disagreement is audited; if at least half are the record carrying non-label information, eventDate moves to auto_fill with that reason.
- country: match 98.6%, wrong 0% [same] -> assist, audit missing [same]. The value comes from the v2 inference rule (a U.S. state on the label means "USA"), so this field measures whether the model read a U.S. state.
- stateProvince: match 97.1%, wrong 0% -> assist, audit missing [fast: wrong 1.4% -> assist; tiebreaker due, same rule as eventDate].
- county: match 90.8%, wrong 6.2% -> do_not_use [89.2%, 7.7% -> do_not_use]. Tiebreaker due for the strong model only (6.2% is within 2 points of the 5% kill bar): every county disagreement is audited; if at least half are the record carrying non-label information, county moves to assist.
- locality: match 34.8% [28.8%] -> do_not_use [do_not_use].
- habitat: match 8.1% [5.4%], omitted 89.2% [91.9%] -> do_not_use [do_not_use].
- The two models agree on every field's tier except stateProvince (strong: assist, audit missing; fast: assist). No auto_fill field today.
- Open interpretation, found while reading the code against this table: `stats.audited_halluc` returns None when a field has no wrong or unsupported rows, which would block auto_fill for country and stateProvince (strong) even after the audit exists, because there is nothing to adjudicate. Pre-registered intent reads as 0 in that case. Not changed after seeing results; the author decides.
- Implementation note (added 2026-11-06 after review): `score.py tier()` returns "assist (audit missing)" before it checks the do_not_use branch, which is a different order from the rule block in section 2. The two agree on every reachable input: match >= 0.95 forces omitted <= 0.05, and wrong <= 0.01 is already required, so no field can meet the first branch and the do_not_use condition at once. Code left as is.

Gate 3 (source `results/model_comparison.csv`): gap strong minus fast = +0.6 points, paired cluster bootstrap 95% CI -0.9 to +2.1, two-sided p 0.453. Gray zone. Decision as written: WORKFLOW.md recommends the fast model (gemini-3-flash-preview) as default, with the strong model as a second pass on fields the fast model left null or the human flagged. The CI is 3.0 points wide, so a true gap of roughly 1.5 points or less could not have been distinguished from zero here (sentence corrected 2026-11-06 after review; the earlier wording said "smaller than about 3.0", which overstated it). H3 is killed.

Gate 4 (sources `results/report_numbers.csv`, `results/reconcile_*_test_gemini-3.1-pro-preview.csv`):
- GBIF: 63 of 69 strong-model names (91.3%) reconcile to the curated accepted key; control 70 of 70 curated names reconcile to their own key. Pass. Decision: name reconciliation is an automatic step in WORKFLOW.md.
- TGN: 31 of 36 distinct curated county strings (86.1%) resolve to one Virginia county. Gray zone. Decision: TGN is used with a local fallback list; the 5 unmatched strings are Hampton City, Lynchburg City, Norfolk, Suffolk City (independent cities, which the query's county type does not cover) and `Wa` (a truncated value in the record itself).
- LC NAF (correction 2026-11-07, after an independent recount: the name splitter produced fragments such as `jr`, and 4 of them matched unrelated LC headings; corrected counts are 18 of 48 strings (37.5%) on the reading below and 15 of 43 real persons (34.9%); the original text is kept unedited for the record): 22 of 48 distinct curated collector strings (45.8%) have a plausible hit, counting a multi-person string as covered when any one person in it has a hit. Stricter readings (post hoc, `results/report_numbers.csv`): every person in the string has a hit, 16 of 48 (33.3%); per distinct person, 19 of 62 (30.6%). No bar; reported as a finding (H5 first half holds under all three). A plausible hit matches initials and surname only; it is not an identity check.

Author overrides, if any, with date and reason: none as of 2026-11-06.
