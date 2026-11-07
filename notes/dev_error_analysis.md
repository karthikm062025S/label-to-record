# Dev error analysis: prompt v1, fast model

Dev split only (30 records), model gemini-3-flash-preview, prompt `prompts/v1.txt`. These numbers were used to write the v2 prompt. They are not evidence about the tool.

Sources: `results/dev_v1_scores.csv` (one row per record and field), `results/dev_v1_summary.csv` (per-field rates and CIs), `results/run_log_dev_v1_flash.txt` (30 records, 29 new calls, 1 cached smoke call, 0 errors).

## Per-field result (dev, v1)

| Field | scorable n | match | main failure |
| --- | --- | --- | --- |
| scientificName | 30 | 0.733 | 5 wrong, 3 partial |
| recordedBy | 30 | 0.767 | 4 partial, 3 wrong |
| recordNumber | 17 | 0.882 | 2 wrong; 5 unsupported of 13 with no curated number |
| eventDate | 30 | 0.067 | 28 wrong |
| country | 30 | 0.033 | 29 omitted |
| stateProvince | 30 | 0.967 | 1 omitted |
| county | 29 | 0.897 | 2 wrong, 1 omitted |
| locality | 26 | 0.346 | 15 partial, 2 wrong |
| habitat | 9 | 0.778 | 15 unsupported of 21 with no curated habitat |

Overall match (unweighted mean of nine fields) 0.608. Sum of wrong plus unsupported: 64 (42 wrong, 22 unsupported).

## Error types, with real examples (gbifID, AI value, curated value)

1. **Date copied in the label's format, not ISO 8601 (28 of 30 eventDate rows).** The scorer only parses ISO dates, so these are all `wrong` even when the date is right.
   - 3893483883: AI `4/8/43`, curated `1943-04-08`
   - 3893450557: AI `July 31, 1932`, curated `1932-07-31`
   - 3893486827: AI `ca. 8 Feb. 1976`, curated `1976-02-08`
   - Some are also real reading disagreements, hidden under the format error: 3893467088 AI `Oct 4, 1930` vs curated `1936-10-04`; 3893454764 AI `Aug. 21, 1907` vs `1907-08-11`; 3893486607 AI `7/20/32` vs `1930-07-30`; 3893483991 AI `AUG 29 1964` vs `1964-08-24`.
   - 3893493822: AI `12-5-71`, curated `1971-05-12`. The record reads it as day-month; a month/day rule would give 1971-12-05. This label is ambiguous and a prompt rule cannot settle it.
   - Rule in v2: ISO 8601 output, partial dates allowed, numeric dates read month/day/year, two-digit years are 19YY.

2. **Country left null (29 of 30).** The labels name Virginia but not the country; the GBIF record fills `United States of America` for every row. v1 told the model to return null for anything not on the label, and it did.
   - 3893483883, 3893439452, 3893450557 and 26 more: AI null, curated `United States of America`.
   - Rule in v2: if the label names a U.S. state and no country, write "USA". This is a deliberate inference from the label, not a transcription, and the report says so. It means country on test measures "did the model read a U.S. state", nothing more.

3. **Habitat split out of the locality text (15 habitat unsupported, 15 locality partial).** The VPI records keep habitat words inside `locality` and fill `habitat` on only 9 of 30 dev records. The model split them, so the same text scored twice as an error.
   - 3893460736: AI locality `east of Ironto`, AI habitat `In moist soil along railroad`; curated locality `In moist soil along railroad east of Ironto`, curated habitat empty.
   - 3893493543: AI locality `Greasy Creek, Va. 764, just west of 765.`, AI habitat `Rocky bank, dense mixed woods`; curated locality `Rocky bank, dense mixed woods, Greasy creek, Va. 764, just west of 765.`
   - 3893457219: AI locality `rt. 668, 1 mile S. of 802.`; curated `Thin woods, rt. 668, 1 mile S. of 802. Petals pale violet at tip, white basally.` (the record also carries a plant description inside locality).
   - Rule in v2: copy the whole locality text verbatim including habitat words; fill habitat only for a label entry headed as habitat. This aligns the AI with the catalog's convention. It is a convention choice, not a reading improvement.

4. **Collector number with a thousands comma (2 wrong).** 3893493557: AI `17,404`, curated `17404`; 3893459182: AI `14,975`, curated `14975`. The pre-registered recordNumber rule does not strip commas, and it stays as registered. Rule in v2: no commas or spaces.

5. **Collector number where the record has none (5 unsupported).** 3893493571 `17121`, 3893460736 `12703`, 3893454764 `365`, 3893485268 `5614`, 3893469174 `6401`, curated empty for all five. Without the image audit these could be real collector numbers the transcriber skipped, or other numbers on the sheet. Rule in v2: the collector's own number only; never a barcode, catalog, accession or sheet number.

6. **Initials run together (3 partial).** 3893485268 and 3893469174: AI `DW Ogle`, curated `D.W.Ogle` / `D. W. Ogle`. The registered normalizer reads `DW` as one given name, so it scores partial. Rule in v2: keep every initial and period as written.

7. **Name differs from the record because the record carries a later determination (4 wrong scientificName, all clubmosses).** 3893483883 AI `Lycopodium flabelliforme (Fern.) Blanch.`, curated `Diphasiastrum digitatum (Dill. ex A.Braun) Holub`; 3893485268 AI `Lycopodium obscurum`, curated `Dendrolycopodium obscurum (L.) A.Haines`; 3893459182 AI `Lycopodium inundatum L.`, curated `Lycopodiella margueritae J.G.Bruce, W.H.Wagner & Beitel`; 3893483991 AI `Lycopodium complanatum L. var. flabelliforme Fern.`, curated `Diphasiastrum digitatum (Dill. ex A.Braun) Holub`. Lycopodium was split into several genera; the record may hold a re-determination that is not on the label, or the sheet may carry an annotation slip the model did not use. GBIF reconciliation (accepted key) tests the first explanation on test. Rule in v2: use the most recent annotation or determination slip if there is one.

8. **Orthography differs from the record (3 partial, 1 wrong).** 3893450557 AI `Eriogonum Alleni S. Wats.` vs `Eriogonum allenii S.Watson`; 3893460736 `Equisetum hiemale, L.` vs `Equisetum hyemale L.`; 3893440560 `Agalinus purpurea` vs `Agalinis purpurea`. The first two look like the label's old spelling against the record's standardized name; the third may be a misreading. Not addressed by v2 (v2 says copy spelling as written); reconciliation is the right tool for this, not the prompt.

9. **County where the record uses a modern or different unit (2 wrong).** 3893454146 AI `Nansemond`, curated `Suffolk` (Nansemond is a former Virginia county, now part of the city of Suffolk, so the label's county is historical and the record modernized it); 3893475209 AI `Virginia Beach`, curated `Virginia Beach City`. Both are the record carrying information that is not on the label. Not addressed by v2.

10. **Collector surname misread (3 wrong).** 3893486607 AI `C.A. Bushland`, curated `C. B. Buckland`; 3893474222 AI `W. R. Garman`, curated `W. R. DeGarmo`; 3893460736 AI `A. B. Massey with Warren Wagner`, curated `A. B. Massey; Warren Wegman, and his class`. These are handwriting reading errors (or the record's reading is the wrong one; only the image audit can say). Not addressed by v2; no prompt rule fixes a misread.

## What v2 changes, and what it cannot change

v2 (`prompts/v2.txt`) adds field rules for types 1 to 7. Types 8 to 10 are reading or record-convention differences that a prompt cannot fix honestly. The examples in v2 are synthetic (`J. Q. Doe`, `1234`, `3/9/52`): an earlier draft used `17404` and `5/17/41 means 1941-05-17`, copied from the errors above, and the leak audit flagged both as a dev record's own curated value, so they were replaced before any v2 call.

Expected effect, stated before the v2 run: eventDate, country and habitat should move the most; scientificName, recordedBy and county should barely move.

## v2 on dev, against v1 (same 30 records, same model)

Source: `results/dev_prompt_comparison.csv` (per field), `results/dev_v2_scores.csv`, `results/dev_v2_summary.csv`, `results/run_log_dev_v2_flash.txt` (30 calls, 0 errors).

| Field | match v1 | match v2 | wrong + unsupported v1 | v2 |
| --- | --- | --- | --- | --- |
| scientificName | 0.733 | 0.633 | 5 | 5 |
| recordedBy | 0.767 | 0.767 | 3 | 2 |
| recordNumber | 0.882 | 0.941 | 7 | 3 |
| eventDate | 0.067 | 0.833 | 28 | 5 |
| country | 0.033 | 1.000 | 0 | 0 |
| stateProvince | 0.967 | 1.000 | 0 | 0 |
| county | 0.897 | 0.897 | 3 | 3 |
| locality | 0.346 | 0.462 | 3 | 2 |
| habitat | 0.778 | 0.222 | 15 | 1 |
| overall | 0.608 | 0.751 | 64 | 21 |

Overall gap v2 minus v1: +0.143, paired cluster bootstrap 95% CI 0.081 to 0.201 (10,000 draws, seed 2026). H2's kill condition (a drop under 5 in wrong + unsupported) did not fire: the drop is 43. v2 is the frozen prompt (PREREGISTRATION.md A1).

What v2 fixed, by type: the ISO date rule turned 23 wrong dates into exact; the country rule filled all 30; the no-comma rule fixed both comma numbers (3893493557 `17404`, 3893459182 `14975`); the county rule now drops "Co." and "County", so those rows went from normalized to exact (no change in match); the habitat rule removed 14 of the 15 unsupported habitats.

What v2 made worse, seen on dev and kept, because the protocol allows one revision only:

- **habitat:** null on 7 of the 9 records where the record has a habitat. Example 3893440560: v1 `Moist meadow` (exact), v2 null, curated `Moist meadow`. The rule asked for a headed "Habitat" entry; these labels write the habitat as a plain line. The curated habitat does not appear in v2's locality text for that record, so this is a real loss, not a move between fields.
- **scientificName:** three Arisaema records went from exact to partial because v2 added `var. triphyllum` (3893493571, 3893493557, 3893493543; curated `Arisaema triphyllum (L.) Schott`). This is probably the most-recent-slip rule picking up an annotation. Two clubmoss records came back with the genus abbreviated as written on a slip: 3893459182 `L. margueritae ?` (curated `Lycopodiella margueritae J.G.Bruce, W.H.Wagner & Beitel`), 3893483991 `L. flabelliforme (Fern.) Blanch.`. For 3893459182 the slip agrees with the record's determination, but the abbreviated genus still scores wrong.
- **recordNumber:** one new omission, 3893434200 (v1 `2056`, v2 null, curated `2056`).
- **eventDate:** the 5 dates still wrong are reading disagreements, not format: 3893454764 `1907-08-21` vs `1907-08-11`, 3893466144 `195` vs `1950`, 3893486607 `1935-07-20` vs `1930-07-30`, 3893493822 `1971-12-05` vs `1971-05-12` (the month/day rule against the record's day/month reading), 3893483991 `1964-08-29` vs `1964-08-24`.

These costs are expected to show up on test too. They go into REPORT.md, not into a v3.
