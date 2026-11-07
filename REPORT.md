# Report: Label to Record

Can a vision model catalog Virginia Tech Massey Herbarium (VPI) specimen sheets into Darwin Core, and where does it fail?

Author: Karthik Mandli, who designed and directed the study; the code and this text were written with Claude Code agents under his review. Written 2026-11-06, after the one frozen test run. Status: **test run complete; image audit not done.** `results/audit_results.csv` does not exist yet, so under the pre-registered stall rule (PREREGISTRATION.md section 2, field 6) every hallucination-type number below is an **auto-scored upper bound, unaudited**, no field can be placed in the auto-fill tier, and H6 is reported as not tested. The audit deadline is 2026-11-11.

Every number here is copied from a file in `results/` or from `notes/report_tables.md` (except the LC NAF counts, corrected 2026-11-07 in section 4; `results/report_numbers.csv` still holds the uncorrected values until `scripts/reconcile.py` is fixed), which `scripts/report_tables.py` prints from those files. The plan is PLAN.md; the decision rules, committed before any model call, are PREREGISTRATION.md.

## 1. Summary

- On 70 held-out sheets, both Gemini models fill eventDate, country and stateProvince correctly for 97 to 99% of records. No field reaches auto-fill, because the bar needs the image audit.
- scientificName, recordedBy, county, locality and habitat land in the "do not use" tier as scored. For three of them, much of the "error" is the catalog, not the model. 7 of the strong model's 8 "wrong" names resolve to the catalog's accepted taxon in the GBIF backbone (H4). The 8 strong-model "unsupported" values are all on the sheet. Locality "wrong" includes verbatim transcriptions that the catalog shortened.
- The image reading turned up catalog remediation work: 5 test records lack a county that is printed on the label, and 3 records have a keying error or truncation (section 7).
- The strong model (gemini-3.1-pro-preview) was not better than the fast one (gemini-3-flash-preview): overall match gap +0.6 points, 95% CI -0.9 to +2.1. The recommendation is the fast model by default.

## 2. Setup

- Pool: VPI Virginia preserved plant specimens on GBIF with a StillImage, restricted to dated records: 11,213 of 52,554 (PLAN.md section 2). The other 41,341 have no collector, date or locality in the catalog. That backlog is the case this tool would be used for, and it is not what was measured (limitation 1).
- Sample: 100 records drawn with seed 2026 under caps (8 per collector, 8 per family, 20 per decade), 274 draws used (`results/manifest_stats.csv`, amendment A3). Split 30 dev / 70 test. The test split covers the 1910s to the 2020s and 43 collector clusters (`results/test_summary.csv` n_clusters). Asteraceae is 8 of 100 against 56% of the pool, by design of the family cap.
- Task: one sheet image plus a fixed prompt, nothing else; JSON with nine Darwin Core terms (scientificName, recordedBy, recordNumber, eventDate, country, stateProvince, county, locality, habitat); temperature 0. The leak audit (`tests/test_leak.py`, and `run_model.py` before each call) checks that no catalog value or identifier reaches the request.
- Prompt: v1 was the baseline. v2 was written from the dev errors (`notes/dev_error_analysis.md`) and frozen by hash before any test call (A1). Dev overall match: v1 0.608, v2 0.751 (`results/dev_prompt_comparison.csv`). These are **dev numbers, used to write the prompt, not evidence**.
- Models: amendment A2 records that the pre-named gemini-2.5-flash and gemini-2.5-pro returned HTTP 404 for this key, so the fast model became gemini-3-flash-preview.
- Ground truth: the curated GBIF record. Scoring categories and per-field normalization rules are pre-registered (PLAN.md 3.4, `scripts/score.py`). CIs are 95% percentile bootstrap, 10,000 draws, seed 2026, clustered by collector, because sheets by one collector share a hand and a label style.
- Calls: 201 cached responses in `results/raw/` (smoke, dev v1, dev v2, 140 test). The test runs had 0 errors (`results/run_log_test_v2_*.txt`).

## 3. Results

Per field, test, both models (source: `results/test_summary.csv`, table printed by `scripts/report_tables.py`):

| Field | Model | scorable n | match % (95% CI) | partial % | wrong % (95% CI) | omitted % | unsupported (n / curated empty) | tier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| scientificName | strong | 70 | 72.9 (60.3 to 84.6) | 14.3 | 11.4 (4.3 to 19.7) | 1.4 | 0 / 0 | do_not_use |
| scientificName | fast | 70 | 72.9 (61.1 to 84.1) | 15.7 | 10.0 (3.1 to 17.9) | 1.4 | 0 / 0 | do_not_use |
| recordedBy | strong | 70 | 72.9 (58.9 to 84.7) | 20.0 | 1.4 (0.0 to 5.0) | 5.7 | 0 / 0 | do_not_use |
| recordedBy | fast | 70 | 74.3 (60.7 to 85.7) | 20.0 | 2.9 (0.0 to 7.1) | 2.9 | 0 / 0 | do_not_use |
| recordNumber | strong | 53 | 83.0 (70.0 to 94.0) | 0.0 | 1.9 (0.0 to 6.7) | 15.1 | 2 / 17 | assist |
| recordNumber | fast | 53 | 86.8 (77.8 to 94.5) | 0.0 | 3.8 (0.0 to 10.3) | 9.4 | 2 / 17 | assist |
| eventDate | strong | 70 | 97.1 (93.1 to 100.0) | 0.0 | 1.4 (0.0 to 4.5) | 1.4 | 0 / 0 | assist |
| eventDate | fast | 70 | 97.1 (93.1 to 100.0) | 0.0 | 1.4 (0.0 to 4.5) | 1.4 | 0 / 0 | assist |
| country | strong | 70 | 98.6 (95.3 to 100.0) | 0.0 | 0.0 (0.0 to 0.0) | 1.4 | 0 / 0 | assist (audit missing) |
| country | fast | 70 | 98.6 (95.3 to 100.0) | 0.0 | 0.0 (0.0 to 0.0) | 1.4 | 0 / 0 | assist (audit missing) |
| stateProvince | strong | 70 | 97.1 (92.5 to 100.0) | 0.0 | 0.0 (0.0 to 0.0) | 2.9 | 0 / 0 | assist (audit missing) |
| stateProvince | fast | 70 | 97.1 (92.7 to 100.0) | 0.0 | 1.4 (0.0 to 4.9) | 1.4 | 0 / 0 | assist |
| county | strong | 65 | 90.8 (82.8 to 97.0) | 0.0 | 6.2 (1.3 to 13.3) | 3.1 | 5 / 5 | do_not_use |
| county | fast | 65 | 89.2 (80.7 to 95.9) | 0.0 | 7.7 (1.6 to 15.7) | 3.1 | 5 / 5 | do_not_use |
| locality | strong | 66 | 34.8 (23.5 to 46.9) | 54.5 | 9.1 (2.9 to 18.2) | 1.5 | 1 / 4 | do_not_use |
| locality | fast | 66 | 28.8 (17.8 to 40.3) | 59.1 | 9.1 (2.9 to 18.2) | 3.0 | 2 / 4 | do_not_use |
| habitat | strong | 37 | 8.1 (0.0 to 17.1) | 2.7 | 0.0 (0.0 to 0.0) | 89.2 | 0 / 33 | do_not_use |
| habitat | fast | 37 | 5.4 (0.0 to 14.3) | 2.7 | 0.0 (0.0 to 0.0) | 91.9 | 0 / 33 | do_not_use |

Overall match, unweighted mean of the nine fields: strong 72.8% (clustered CI 69.2 to 76.3; per-record CI 69.1 to 76.2), fast 72.2% (68.6 to 75.6; 68.6 to 75.6). The overall number averages very different fields and is never the headline on its own.

Cost and speed (`results/report_numbers.csv`): median latency was 4.175 s for the strong model and 6.265 s for the fast one. The "fast" model used a mean of 3945.7 thinking tokens per record, against 32.5 for the strong model, on the same 1603-token input. On this task the model labeled fast was the slower one.

## 4. Pre-registered gate verdicts (copied from PREREGISTRATION.md section 8)

- **Gate 2, field tiers.** The two models agree on every field's tier except stateProvince (strong: assist, audit missing; fast: assist). No auto_fill field today. Tiebreaker audits are due for eventDate (both models; wrong 1.4% sits 0.4 points above the 1% bar), stateProvince (fast) and county (strong; 6.2% is within 2 points of the 5% kill bar). Each tiebreaker audits every disagreement for that field, and the tier moves up only if at least half are the record carrying non-label information.
- **Gate 3, model comparison.** Gap +0.6 points, paired cluster bootstrap 95% CI -0.9 to +2.1, two-sided p 0.453 (`results/model_comparison.csv`). Gray zone. Decision as written: the fast model is the default and the strong model is a second pass. The CI is 3.0 points wide, so a true gap of roughly 1.5 points or less could not have been distinguished from zero here.
- **Gate 4, reconciliation.** GBIF: 63 of 69 strong-model names (91.3%) reconcile to the catalog's accepted key, and the control is 70 of 70. Pass, so name reconciliation is an automatic step. TGN: 31 of 36 distinct catalog county strings (86.1%) resolve to one Virginia county. Gray zone, so TGN is used with a local fallback list. The 5 unmatched strings are four independent cities and the truncated value `Wa`. LC NAF (corrected 2026-11-07: the name splitter broke "Surname, Given" strings into fragments, and 4 fragments (jr, greg, stan, patrick) matched unrelated LC headings, so the first published counts (22 of 48 strings, 19 of 62 persons) were inflated): 18 of 48 distinct catalog collector strings (37.5%) have a plausible hit when a multi-person string counts as covered if any one person has a hit. Stricter readings, post hoc: 16 of 48 (33.3%) when every person must have a hit, and 15 of 43 real persons (34.9%).

## 5. Hypotheses (PLAN.md section 5)

- **H1 (field tiers): killed.** It predicted scientificName, country and stateProvince at auto-fill, and recordedBy, eventDate and county at assist or better. scientificName (72.9%) and recordedBy (72.9%) fell below the 80% assist bar, and county hit the wrong-rate kill bar (6.2%). Country and stateProvince could not reach auto-fill without the audit. The part that held: locality and habitat did not reach auto-fill.
- **H2 (prompt rules help, dev only, exploratory): holds.** Dev wrong + unsupported fell from 64 to 21 between v1 and v2 (A1), well past the 5-count bar. It came with known costs: habitat and scientificName match fell on dev, and the v2 habitat rule is the main reason habitat is 89% omitted on test (section 6.4).
- **H3 (strong model at least 5 points better): killed.** Gap +0.6, CI includes 0.
- **H4 (synonyms hide inside "wrong"): holds.** 7 of 8 (87.5%) strong-model `wrong` scientificName values reconcile to the catalog's accepted taxon key (`results/reconcile_gbif_test_gemini-3.1-pro-preview.csv`).
- **H5 (vocabulary fit): first half holds, second half killed.** LC NAF coverage is under 50% on all three readings above. TGN resolved 86.1% of catalog county strings, under the 90% the hypothesis needed.
- **H6 (non-label information in the record): not tested.** The audit is missing. Under the stall rule this stays "not tested" until `results/audit_results.csv` exists.

## 6. What "wrong" and "unsupported" contain

The scorer cannot see the label, so a disagreement means "differs from the catalog string", not "AI error". After the test run, a second Claude Code agent, acting as independent reviewer, read the label images behind the strong model's scientificName and unsupported disagreements and the main locality and county cases. The rows are listed with gbifIDs so anyone can check them against the image URL in `data/manifest.csv`. These readings are not the pre-registered audit and do not change a tier.

### 6.1 scientificName: 8 strong-model "wrong" rows, 0 confirmed reading errors

| Cause | Count | gbifIDs |
| --- | --- | --- |
| Label name copied exactly; the catalog carries a later name (re-determination or synonym) | 5 | 3893443281 (label "Cacalia atriplicifolia L."), 3893438702 ("Aster undulatus, L"), 3893483692 ("Lycopodium digitatum A. Braun"), 3893493321 (AI "Kuhnia eupatorioides"), 3893439728 (AI "Orchis spectabilis") |
| Scorer artifact: the AI copied the diaeresis from the newest slip ("Isoëtes"), the catalog has "Isoetes"; the genus is compared byte-wise, so it scores wrong instead of normalized | 2 | 3893461253, 3893447816 |
| Abbreviated genus ("L. flabelliforme"); the only one of the 8 that does not reconcile | 1 | 3893483881 |

The reviewer read the label image for 3893443281, 3893438702, 3893483692 and 3893461253. For 3893493321 and 3893439728 the evidence is that they reconcile to the catalog's accepted key; those sheets were not read. The diacritic gap is logged as amendment A4, and the registered scorer is left unchanged.

### 6.2 Unsupported: 8 strong-model rows, every value is on the sheet

"Unsupported" means the AI filled a field the catalog leaves empty. All 8 values appear on the sheet:
- County printed on the label, catalog county empty: 3893442526 ("Amelia Co."), 3893448535 ("DICKENSON: VA."), 3893473689 ("VIRGINIA: Floyd County"), 3893454283 ("Sussex: 9 May 1961"), 3893452809 ("Montgomery: 16 May 1961").
- recordNumber "137" written above "Collector": 3893450366.
- locality "No locality data." copied from the label line itself: 3893446135. It is on the label, but it is not a place.
- recordNumber "EF25", a pencil mark below the E. Farr label on 3893471419. It may be Farr's own number. It sits outside the label fields, so it is a judgment call for the audit.

So the pooled unsupported rate (strong 8 of 59, 13.6%, `results/report_numbers.csv`) is an upper bound that the image reading does not support as hallucination. This report does not call these rows hallucinations. The audited number waits for `results/audit_results.csv`.

### 6.3 locality: "wrong" and "partial" measure distance from the catalog's convention

The v2 prompt asks for the whole locality text verbatim. The catalog often keeps a shortened or reworded version. The Jaccard and containment rule then scores a correct transcription as wrong:
- 3893483692: the AI copied the full label paragraph (habitat, associates, "Rt. 690, 1.6 mi. S of the town of Poages Mill and Rt. 211."). The catalog kept "Rt 690 1.6 mi S of Poages Mill and Rt 211", and containment fails on "the town of".
- 3893450366: AI "Mariner's Museum - open woods" is exactly the label. Catalog "Mariners' Museum"; after punctuation stripping, "mariner s" does not contain "mariners".
- 3893461253: the label reads "In Bear Creek Lake." and the AI matches it; the catalog says "On Bear Creek." The AI left out the line "By mail from E. J. Seay, Jr.", which is provenance, not place.

The scorer stays as registered. Locality match (strong 34.8%) is not a reading-accuracy number.

### 6.4 habitat: a prompt decision, not a reading failure

The v2 rule says to fill habitat only when the label has its own "Habitat" entry, and to keep habitat words inside locality. Habitat is omitted on 89.2% of scorable records (strong). For 24 of those 33 omitted rows (72.7%), the catalog's habitat text is found inside the AI's locality (`results/report_numbers.csv`, post hoc). The cost was visible on dev before the freeze and was left in place, because the protocol allowed one revision (A1).

### 6.5 county: the four strong-model "wrong" rows

- Warwick vs catalog "Wa" (3893450366): the label reads "Warwick Co.", so the catalog value is truncated.
- "Wash" vs "Washington" (3893447105): the label abbreviation; the catalog expanded it.
- "City of Suffolk" vs "Suffolk City" (3893444632) and "Hampton" vs "Hampton City" (3893487798): the same places, written in a different convention for Virginia independent cities.

The reviewer read the images for the first two. None of the four is a misread place name. The pre-registered tiebreaker audit decides whether county moves up a tier.

### 6.6 Real AI errors found

The error types confirmed against the image, for the taxonomy:
- **Digit misread:** 3893438702 eventDate 1939-09-18; the label reads "Sept. 10. 1939". Both models made it.
- **Place name read as collector:** 3893446433, fast model recordedBy "Eggleston". That is the locality line; the collector line reads "A. B. Massey", which the strong model got.
- **Truncated number:** 3893447105, fast model recordNumber "203". The red stamp reads "2032", with the last digit at the label edge.
- **Initial misread:** 3893461253, strong model recordedBy "E. S. Seay, Jr." for "E. J. Seay, Jr." It is scored partial, because the catalog itself has a different surname spelling (section 7).

Also scored wrong but correct to the label: 3893483692 recordNumber "896:96", where the label prints a colon and the catalog writes 896-96.

### 6.7 recordedBy partials

20% of recordedBy rows score partial for both models. Post hoc, 6 of the strong model's 14 partial rows (42.9%) match after reordering the catalog's "Surname, Given" form (`results/report_numbers.csv`). The registered normalizer splits on commas, so "Harvill, A. M., Jr." becomes three parts. That is a scorer limit, not a model limit.

## 7. Catalog findings (remediation output)

Catalog gaps found: county printed on the label but empty in the catalog.

| gbifID | catalogNumber | label county | image |
| --- | --- | --- | --- |
| 3893442526 | VPI-V-0032505 | Amelia Co. | https://media01.symbiota.org/media/seinet/sernec/VPI/VPI-V-0032/VPI-V-0032505.jpg |
| 3893448535 | VPI-V-0032517 | DICKENSON: VA. | https://media01.symbiota.org/media/seinet/sernec/VPI/VPI-V-0032/VPI-V-0032517.jpg |
| 3893473689 | VPI-V-0040916 | VIRGINIA: Floyd County | https://media01.symbiota.org/media/seinet/sernec/VPI/VPI-V-0040/VPI-V-0040916.jpg |
| 3893454283 | VPI-V-0032777 | Sussex | https://media01.symbiota.org/media/seinet/sernec/VPI/VPI-V-0032/VPI-V-0032777.jpg |
| 3893452809 | VPI-V-0032713 | Montgomery | https://media01.symbiota.org/media/seinet/sernec/VPI/VPI-V-0032/VPI-V-0032713.jpg |

Catalog corrections proposed (the label image supports the AI value):

| gbifID | field | catalog value | label value | image |
| --- | --- | --- | --- | --- |
| 3893434570 | recordedBy | A. M. Hawell | A M Harvill 12300 (the same botanist signs "Det: A.M. Harvill Jr" on 3893443281) | https://media01.symbiota.org/media/seinet/sernec/VPI/VPI-V-0033/VPI-V-0033940.jpg |
| 3893450366 | county | Wa | Warwick Co. | https://media01.symbiota.org/media/seinet/sernec/VPI/VPI-V-0034/VPI-V-0034741.jpg |
| 3893450366 | recordNumber | (empty) | 137 | same as above |
| 3893461253 | recordedBy | E. J. Seary Jr. | E. J. Seay, Jr. | https://media01.symbiota.org/media/seinet/sernec/VPI/VPI-V-0000/VPI-V-0000141_S1.jpg |

These are proposals for a collections manager to confirm, not edits. The "Hawell" typo also splits one collector into two clusters in the bootstrap (`results/manifest_stats.csv` lists both "a m hawell" and "a m; harvill; jr").

## 8. Dublin Core crosswalk

`scripts/crosswalk.py` writes simple Dublin Core from the strong model's output (`results/dublin_core.csv`) and from the catalog (`results/dublin_core_curated.csv`), one row per record, for diffing. The mapping:
- scientificName to dc:subject, which also builds dc:title.
- recordedBy to dc:creator (a cultural-heritage profile might prefer dc:contributor).
- recordNumber and catalogNumber to dc:identifier.
- The four place fields to one dc:coverage string.
- habitat to dc:description; the license to dc:rights.
- Constants: dc:type PhysicalObject and dc:publisher.

After review, the specimen record no longer carries dc:format image/jpeg or dc:relation, because that mixed the specimen and its photograph in one record, against the DCMI one-to-one principle. The image URL is now dcterms:hasFormat, and a full profile would give the photograph its own record (A7).

## 9. Recommended workflow

WORKFLOW.md section 7 has the field-by-field table. In short:
- eventDate, country, stateProvince: the AI pre-fills, a person confirms. These are the auto-fill candidates once the audit is in.
- recordNumber: pre-fill, check every value and every null.
- scientificName: reconcile to the GBIF backbone. Accept when the accepted key matches the expected taxon, and queue the rest for a person (6 of 69 here).
- recordedBy, county, locality, habitat: draft only. For skeletal records with an empty catalog, though, the county and locality drafts are where the tool adds the most, as section 7 shows.
- Model: fast by default; strong as a second pass on nulls and flagged values.

## 10. Limitations

1. Selection: the sample is dated records, already transcribed, while the backlog is the 41,341 skeletal records. Their labels may be older or harder to read. Asteraceae is deliberately under-represented (A3).
2. Ground truth is the catalog, which carries later determinations, conventions, gaps and typos (sections 6 and 7). The automatic rates therefore overstate AI error. The audit is what corrects this, and it is not done.
3. One test record, 5131791191, is a 40x bryophyte micrograph with no label (its image URL contains "Branch40x"). The plant filter let it through. Both models returned null on all nine fields, so it is scored omitted on every scorable field, which costs about 1.4 points of match on each field. It is reported, not removed.
4. n = 70 records in 43 collector clusters. The CIs are wide; for example, scientificName match is 60.3 to 84.6.
5. The adjudicator is not a botanist. The reviewer readings in section 6 cover only some rows, and because they are discussed here by name, the author's audit is not blind for those rows (A8).
6. Dev v1 calls began 1 minute 35 seconds before the harness commit (A5). Dev only; every test call ran on committed, frozen code.
7. The scorer has known gaps, found after the test: diacritics (A4), locality convention distance (6.3) and "Surname, Given" names (6.7). They stay as registered, so the numbers are conservative against the model.
8. The committed viewer embeds two open-licence fonts; a rebuild uses system fonts (WORKFLOW.md section 8).

## 11. What I would change next

These changes would alter the prompt or the scorer after seeing test results, so they are not applied here. They are for a v3 run on fresh dev data, with a new freeze.
- Scorer: Unicode NFKD and strip combining marks before every comparison (A4). Reorder "Surname, Given" before name normalization. Treat `:` and `-` in recordNumber as equivalent. Add the Virginia independent-city convention ("City of X" = "X City" = "X") to county.
- Locality scoring: add a token-recall measure (share of catalog tokens found in the AI text), so a verbatim transcription that contains the catalog string scores as covering it.
- Prompt: split habitat out of locality when the label text marks it as habitat; the v2 rule cost 89% omission. Also, never put a pencil mark outside the label fields into recordNumber.
- Audit verdicts: add a fifth verdict for "the label supports the AI and the catalog is empty or mistyped", because the four registered verdicts do not fit it (A8).
- Sampling: add a "label visible" check in `scripts/sample.py` or `fetch_images.py` to drop micrographs and label-less photos.
- Sample from the skeletal records too. There, accuracy can only be judged by reading images, but that is where the tool would be used.

## 12. Prior work

Checked 2026-11-06 by search; I have read the abstracts, not the full papers:
- Guralnick, R., LaFrance, R., Allen, J. M., and Denslow, M. W. "Ensemble automated approaches for producing high-quality herbarium digital records." Applications in Plant Sciences 13(1): e11623, 2025 (online November 2024; https://pmc.ncbi.nlm.nih.gov/articles/PMC11788903/). They compare a rule-based pipeline with ChatGPT-4 on OCR text from typewritten labels, measuring omission and commission errors per Darwin Core field, and argue for an ensemble.
- Weaver, W. N., et al. "The Future of Natural History Transcription: Navigating AI advancements with VoucherVision and the Specimen Label Transcription Project (SLTP)." Biodiversity Information Science and Standards 7: e113067, 2023, a conference abstract (https://biss.pensoft.net/article/113067/). It pairs OCR with large language models to turn label text into database-ready fields.

What this study does differently: it is zero-shot from the image alone with no OCR step, it is scored against the published catalog record rather than a fresh gold transcription, its decision rules were pre-registered before any model call, and it measures controlled-vocabulary fit (GBIF backbone, Getty TGN, LC NAF) beside accuracy.

## 13. Files

- Decision rules and amendments: `PREREGISTRATION.md`. Plan: `PLAN.md` (section 8 maps planned paths to real ones). Rerun steps: `WORKFLOW.md`.
- Scores: `results/test_<model>_scores.csv`. Summary with CIs and tiers: `results/test_summary.csv`. Comparison: `results/model_comparison.csv`. Derived numbers: `results/report_numbers.csv`. Tables: `notes/report_tables.md`.
- Reconciliation: `results/reconcile_{gbif,tgn,lcnaf}_test_gemini-3.1-pro-preview.csv`. Dublin Core: `results/dublin_core*.csv`.
- Audit: `results/audit_sample.csv` (60 rows to adjudicate), `results/audit_proposals.csv` (a reviewer's proposed verdicts for 40 rows, not the audit), and `results/audit_results.csv` (the author's, not yet written).
- Viewer: `viewer.html` (built by `scripts/build_viewer.py`); screenshots in `screenshots/`.
- Tests: `python -m unittest discover tests` (scoring rules, leak audit, manifest checks).
