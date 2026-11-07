> Correction 2026-11-07: the LC NAF rows below are uncorrected script output. The name splitter counted fragments such as `jr`, and 4 matched unrelated LC headings. Corrected: 18 of 48 curated strings (37.5%), 15 of 43 real persons (34.9%). See REPORT.md section 4.

Per field, test, both models (source: results/test_summary.csv)

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

Overall match, unweighted mean of nine fields (source: results/test_summary.csv)

| Model | overall match % | 95% CI, clustered by collector | 95% CI, per record |
| --- | --- | --- | --- |
| strong (gemini-3.1-pro-preview) | 72.8 | 69.2 to 76.3 | 69.1 to 76.2 |
| fast (gemini-3-flash-preview) | 72.2 | 68.6 to 75.6 | 68.6 to 75.6 |

Model comparison (source: results/model_comparison.csv)

| gap strong minus fast, points | 95% CI | two-sided p | CI excludes 0 |
| --- | --- | --- | --- |
| 0.6 | -0.9 to 2.1 | 0.453 | False |

Derived numbers (source: results/report_numbers.csv)

| Number | value | n / d | kind |
| --- | --- | --- | --- |
| gemini-3-flash-preview total wrong (all fields) | 24 |  | preregistered |
| gemini-3-flash-preview total unsupported (all fields) | 9 |  | preregistered |
| gemini-3-flash-preview total omitted (all fields) | 49 |  | preregistered |
| gemini-3-flash-preview total partial (all fields) | 65 |  | preregistered |
| gemini-3-flash-preview pooled unsupported rate (AI filled / curated empty, all fields; unaudited upper bound) | 15.2% | 9 / 59 | post_hoc |
| gemini-3-flash-preview wrong + unsupported share of AI-filled values (AI-filled = ai_value non-empty, incl. 's.n.') | 6.2% | 33 / 529 | post_hoc |
| gemini-3-flash-preview records with every field null | 1 |  | preregistered |
| gemini-3-flash-preview test calls (attempts) | 70 |  | preregistered |
| gemini-3-flash-preview median latency s | 6.265 |  | preregistered |
| gemini-3-flash-preview mean prompt tokens | 1603.0 | 112210 / 70 | preregistered |
| gemini-3-flash-preview mean output tokens | 109.8571 | 7690 / 70 | preregistered |
| gemini-3-flash-preview mean thinking tokens | 3945.6857 | 276198 / 70 | preregistered |
| gemini-3-flash-preview recordedBy partial rows that match after reordering 'Surname, Given' | 50.0% | 7 / 14 | post_hoc |
| gemini-3-flash-preview habitat omitted rows whose curated habitat is inside the AI locality | 73.5% | 25 / 34 | post_hoc |
| gemini-3.1-pro-preview total wrong (all fields) | 21 |  | preregistered |
| gemini-3.1-pro-preview total unsupported (all fields) | 8 |  | preregistered |
| gemini-3.1-pro-preview total omitted (all fields) | 53 |  | preregistered |
| gemini-3.1-pro-preview total partial (all fields) | 61 |  | preregistered |
| gemini-3.1-pro-preview pooled unsupported rate (AI filled / curated empty, all fields; unaudited upper bound) | 13.6% | 8 / 59 | post_hoc |
| gemini-3.1-pro-preview wrong + unsupported share of AI-filled values (AI-filled = ai_value non-empty, incl. 's.n.') | 5.5% | 29 / 524 | post_hoc |
| gemini-3.1-pro-preview records with every field null | 1 |  | preregistered |
| gemini-3.1-pro-preview test calls (attempts) | 70 |  | preregistered |
| gemini-3.1-pro-preview median latency s | 4.175 |  | preregistered |
| gemini-3.1-pro-preview mean prompt tokens | 1603.0 | 112210 / 70 | preregistered |
| gemini-3.1-pro-preview mean output tokens | 119.2286 | 8346 / 70 | preregistered |
| gemini-3.1-pro-preview mean thinking tokens | 32.4714 | 2273 / 70 | preregistered |
| gemini-3.1-pro-preview recordedBy partial rows that match after reordering 'Surname, Given' | 42.9% | 6 / 14 | post_hoc |
| gemini-3.1-pro-preview habitat omitted rows whose curated habitat is inside the AI locality | 72.7% | 24 / 33 | post_hoc |
| gate4 GBIF: AI accepted key equals curated, where AI name not omitted | 91.3% | 63 / 69 | preregistered |
| gate4 GBIF control: curated name reconciles to its own accepted key | 100.0% | 70 / 70 | preregistered |
| H4: strong wrong scientificName that reconcile to the curated accepted key | 87.5% | 7 / 8 | preregistered |
| H4: strong partial scientificName that reconcile to the curated accepted key | 60.0% | 6 / 10 | post_hoc |
| strong string-match scientificName that also reconcile | 98.0% | 50 / 51 | post_hoc |
| gate4 TGN: distinct curated county strings resolving to one Virginia county | 86.1% | 31 / 36 | preregistered |
| gate4 LC NAF: distinct curated collector strings with a plausible hit (any one person in the string) | 45.8% | 22 / 48 | preregistered |
| LC NAF: distinct curated collector strings where every person has a plausible hit | 33.3% | 16 / 48 | post_hoc |
| LC NAF: distinct curated normalized persons with a plausible hit | 30.6% | 19 / 62 | post_hoc |
| gate4 TGN: distinct ai county strings resolving to one Virginia county | 86.5% | 32 / 37 | preregistered |
| gate4 LC NAF: distinct ai collector strings with a plausible hit (any one person in the string) | 52.3% | 23 / 44 | preregistered |
| LC NAF: distinct ai collector strings where every person has a plausible hit | 36.4% | 16 / 44 | post_hoc |
| LC NAF: distinct ai normalized persons with a plausible hit | 37.2% | 19 / 51 | post_hoc |
