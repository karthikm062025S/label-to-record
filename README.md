# Label to Record

A pre-registered test of whether an AI vision model can turn a photographed herbarium specimen label into a catalog record, and where it fails.

**The question.** Herbaria hold millions of pressed plants whose catalog records are thin: many have a photo of the label but little typed data. Can a vision model read the label and fill in the record well enough to help a cataloger? **The answer so far:** on 70 held-out Massey Herbarium (Virginia Tech) sheets, two Gemini models match the catalog for date, country and state about 97 to 99% of the time, and are weak on locality and habitat. No field is safe to fill in automatically, because the human check of the model's mistakes has not been done yet. Many apparent "errors" turned out to be the catalog being out of date, which is useful to a curator in its own right.

## Headline results

Share of the 70 test records where the model's value matches the catalog (`results/test_summary.csv`). Fast is `gemini-3-flash-preview`, Strong is `gemini-3.1-pro-preview`. recordNumber is scored only on the 53 sheets where the catalog has one.

| Field | Fast | Strong |
| --- | --- | --- |
| scientificName | 72.9% | 72.9% |
| recordedBy | 74.3% | 72.9% |
| recordNumber | 86.8% | 83.0% |
| eventDate | 97.1% | 97.1% |
| country | 98.6% | 98.6% |
| stateProvince | 97.1% | 97.1% |
| county | 89.2% | 90.8% |
| locality | 28.8% | 34.8% |
| habitat | 5.4% | 8.1% |

## Key findings

- Of the Strong model's 8 "wrong" scientific names, 5 were the older name printed on the label that the catalog has since updated, and 2 were a diacritic scoring artifact (for example ë versus e). So 7 of 8 are not model errors.
- All 8 of the Strong model's "unsupported" values (a value the catalog lacks) were actually written on the sheet.
- 5 catalog records are missing a county that is printed on the label (listed in REPORT.md section 7).
- Name checking against GBIF (a global species-name service): 63 of 69 of the Strong model's names resolve to the catalog's accepted taxon.
- Place checking against Getty TGN (a place-name thesaurus): 31 of 36 catalog county strings resolve to one Virginia county. The county-level query misses Virginia's independent cities.
- Collector checking against LC NAF (the Library of Congress name authority file): a plausible match for 15 of 43 real collectors. This was corrected on 2026-11-07 from an inflated 19 of 62 (a name-splitting bug); see REPORT.md section 4.

## Honest status

- The pre-registered human check of 60 model-versus-catalog disagreements against the label images is **not done**. Every "hallucination" number is therefore an unaudited upper bound, and no field reaches the auto-fill tier.
- n = 70 records, all dated records that were already transcribed. The real backlog is skeletal records with harder labels, so results may not carry over.
- Two models, one frozen prompt, one run.

## What is in this repo

- `REPORT.md`: start here. Findings, tables, limitations.
- `PREREGISTRATION.md`: the pass and kill rules, committed before any model call, with dated amendments.
- `PLAN.md`: the method in detail.
- `WORKFLOW.md`: how to rerun the study or run it on a new set of records.
- `viewer.html`: every test sheet beside the catalog and both models' values. It needs internet, because the sheet images load from their source.
- `results/`: scores, summaries, reconciliation output, and `results/raw/`, the raw model responses (the evidence behind every number).
- `scripts/`, `tests/`, `prompts/`, `data/`: code, checks, the frozen prompt, and the sample list. `notes/` and `screenshots/` hold working notes and viewer screenshots.

## Glossary

- **Darwin Core**: the standard set of field names (scientificName, eventDate, county...) for biodiversity records.
- **Dublin Core**: a general-purpose library metadata standard; the records are also crosswalked to it.
- **GBIF**: the Global Biodiversity Information Facility, which aggregates specimen records and publishes a species-name backbone.
- **Controlled vocabulary**: an agreed list of preferred terms (names, places) so the same thing is always spelled the same way.
- **Reconciliation**: matching a free-text value to its entry in a controlled vocabulary.
- **Getty TGN**: the Getty Thesaurus of Geographic Names.
- **LC NAF**: the Library of Congress Name Authority File.
- **Pre-registration**: writing down the test and the decision rules before running it, so results cannot be bent afterward.

## How to run

Python 3.12, standard library only. Set the key in the environment, never in a file: `GEMINI_API_KEY`. Download the images with `python scripts/fetch_images.py` (they are not stored here; 2 of the 17 tests read them and fail without them), then check the code with:

```
python -m unittest discover tests
```

The full sequence is in `WORKFLOW.md`.

## Credits

Designed and directed by Karthik Mandli; code and text written with Claude Code agents under his review.

Data and image credit: records are from the GBIF dataset "Virginia Polytechnic Institute and State University, Massey Herbarium" (doi:10.15468/8xf679), CC BY 4.0. Images are hot-linked from SERNEC/Symbiota, 69 of 70 under CC BY 4.0 and one under CC BY-NC 4.0, and are not redistributed here.
