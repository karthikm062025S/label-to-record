"""Scoring, normalization, tier, bootstrap, crosswalk and manifest checks.  python -m unittest discover tests

One example per pre-registered normalization rule (PLAN.md 3.4). Pure functions only, no network.
"""
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from common import FIELDS, MANIFEST, load_manifest  # noqa: E402
from crosswalk import to_dc  # noqa: E402
from fetch_images import image_for  # noqa: E402
from sample import CAP  # noqa: E402
from score import collector_key, norm_sciname, parse_date, rates, score_field, tier  # noqa: E402
from stats import ci, paired, percentile, resamples  # noqa: E402
from report_numbers import surname_first  # noqa: E402


class Categories(unittest.TestCase):
    def test_empty_cases(self):
        self.assertEqual(score_field("locality", None, ""), "both_empty")
        self.assertEqual(score_field("locality", "", "Brush Mountain"), "omitted")
        self.assertEqual(score_field("habitat", "oak woods", ""), "unsupported")
        self.assertEqual(score_field("county", "  Montgomery ", "Montgomery"), "exact")  # whitespace collapse

    def test_scientific_name(self):
        self.assertEqual(norm_sciname("Packera obovata (Muhl. ex Willd.) W.A.Weber & A.Love"), "packera obovata")
        self.assertEqual(norm_sciname("Quercus alba L. var. latiloba Sarg."), "quercus alba var. latiloba")
        self.assertEqual(norm_sciname("Rhus copallina L. f."), "rhus copallina")  # 'L. f.' is an author
        self.assertEqual(score_field("scientificName", "Packera obovata", "Packera obovata (Muhl.) W.A.Weber"),
                         "normalized")
        self.assertEqual(score_field("scientificName", "Packera aurea", "Packera obovata"), "partial")
        self.assertEqual(score_field("scientificName", "Senecio obovatus", "Packera obovata"), "wrong")

    def test_recorded_by(self):
        self.assertEqual(score_field("recordedBy", "A.B. Massey", "A. B. Massey"), "normalized")
        self.assertEqual(score_field("recordedBy", "Massey, A. B.", "A. B. Massey"), "normalized")
        self.assertEqual(score_field("recordedBy", "R. Kral & L. J. Uttal", "L.J. Uttal and R. Kral"), "normalized")
        self.assertEqual(score_field("recordedBy", "A. B. Massey", "A. B. Massey; J. B. Lewis"), "partial")
        self.assertEqual(score_field("recordedBy", "Lena Artz", "R. Kral"), "wrong")
        self.assertEqual(collector_key("L.J. Uttal"), collector_key("L. J. Uttal"))

    def test_record_number(self):
        self.assertEqual(score_field("recordNumber", "No. 6927", "6927"), "normalized")
        self.assertEqual(score_field("recordNumber", "#6927", "6927"), "normalized")
        self.assertEqual(score_field("recordNumber", None, "s.n."), "normalized")  # unnumbered = null
        self.assertEqual(score_field("recordNumber", "sn", "s. n."), "normalized")
        self.assertEqual(score_field("recordNumber", "s.n.", ""), "both_empty")
        self.assertEqual(score_field("recordNumber", "6927", ""), "unsupported")
        self.assertEqual(score_field("recordNumber", None, "6927"), "omitted")
        self.assertEqual(score_field("recordNumber", "6972", "6927"), "wrong")

    def test_event_date(self):
        self.assertEqual(parse_date("1970-05-05T00:00:00"), (1970, 5, 5))
        self.assertEqual(parse_date("1936-05-03/1936-05-10"), (1936, 5, 3))
        self.assertEqual(score_field("eventDate", "1936-5-3", "1936-05-03"), "normalized")
        self.assertEqual(score_field("eventDate", "1936", "1936-05-03"), "partial")
        self.assertEqual(score_field("eventDate", "1936-06", "1936-05-03"), "wrong")  # month contradicts
        self.assertEqual(score_field("eventDate", "3 May 1936", "1936-05-03"), "wrong")  # not ISO 8601

    def test_places(self):
        self.assertEqual(score_field("country", "U.S.A.", "United States of America"), "normalized")
        self.assertEqual(score_field("country", "Canada", "United States of America"), "wrong")
        self.assertEqual(score_field("stateProvince", "Va.", "Virginia"), "normalized")
        self.assertEqual(score_field("stateProvince", "West Virginia", "Virginia"), "wrong")
        self.assertEqual(score_field("county", "Montgomery Co.", "Montgomery"), "normalized")
        self.assertEqual(score_field("county", "Montgomery County", "Montgomery"), "normalized")

    def test_free_text(self):
        self.assertEqual(score_field("locality", "Brush Mtn., near Blacksburg", "brush mtn near blacksburg"),
                         "normalized")
        self.assertEqual(score_field("locality", "Brush Mtn near Blacksburg", "Brush Mtn, 2 mi near Blacksburg"),
                         "partial")  # Jaccard 4/6
        self.assertEqual(score_field("habitat", "oak woods", "In thin oak woods on slope"), "partial")  # contained
        self.assertEqual(score_field("habitat", "roadside ditch", "In thin oak woods"), "wrong")


class PostHoc(unittest.TestCase):
    def test_surname_first_diagnostic(self):
        """report_numbers.py post-hoc check: the record's 'Surname, Given' order, never used for tiers."""
        self.assertEqual(surname_first("Wieboldt, Thomas F.; Croy, S. Q."), "Thomas F. Wieboldt; S. Q. Croy")
        self.assertEqual(surname_first("Harvill, Alton M., Jr."), "Alton M. Harvill")
        self.assertEqual(surname_first("T. F. Wieboldt"), "T. F. Wieboldt")


class Rates(unittest.TestCase):
    def test_denominators(self):
        r = rates(["exact", "normalized", "wrong", "omitted", "unsupported", "both_empty"])
        self.assertEqual(r["n_scorable"], 4)
        self.assertEqual(r["match"], 0.5)
        self.assertEqual(r["unsupported"], 0.5)

    def test_tiers(self):
        self.assertEqual(tier(0.96, 0.0, 0.0, 0.0), "auto_fill")
        self.assertEqual(tier(0.96, 0.0, 0.0, None), "assist (audit missing)")
        self.assertEqual(tier(0.96, 0.02, 0.0, 0.0), "assist")
        self.assertEqual(tier(0.79, 0.0, 0.0, 0.0), "do_not_use")
        self.assertEqual(tier(0.90, 0.06, 0.0, 0.0), "do_not_use")
        self.assertEqual(tier(0.85, 0.0, 0.0, None), "assist")


class Bootstrap(unittest.TestCase):
    def test_percentile_matches_numpy_linear(self):
        self.assertAlmostEqual(percentile([0, 1, 2, 3, 4], 0.025), 0.1)

    def test_cluster_resample_keeps_clusters_whole(self):
        draws = resamples(["a", "a", "b"], n_boot=50)
        for ix in draws:
            self.assertEqual(ix.count(0), ix.count(1))  # records 0 and 1 always travel together

    def test_ci_and_paired(self):
        hits = [1] * 30 + [0] * 10
        draws = resamples([i // 2 for i in range(40)], n_boot=2000)
        lo, hi, _ = ci(lambda ix: sum(hits[i] for i in ix) / len(ix), draws)
        self.assertTrue(lo < 0.75 < hi)
        same = paired(lambda ix: 0.5, lambda ix: 0.5, draws)
        self.assertFalse(same["excludes_zero"])
        sep = paired(lambda ix: 1.0, lambda ix: 0.0, draws)
        self.assertTrue(sep["excludes_zero"] and sep["p_is_floor"])


class Crosswalk(unittest.TestCase):
    def test_to_dc(self):
        dc = to_dc({"scientificName": "Packera obovata", "recordedBy": "L. J. Uttal", "recordNumber": "6927",
                    "eventDate": "1970-05-05", "country": "United States of America", "stateProvince": "Virginia",
                    "county": "Roanoke", "locality": "Bennett Springs", "habitat": None},
                   "VPI-V-0016160", "https://example.org/a.jpg", "CC BY 4.0")
        self.assertEqual(dc["dc:title"], "Herbarium specimen: Packera obovata")
        self.assertEqual(dc["dc:identifier"], "collector-number:6927 | VPI-V-0016160")
        self.assertEqual(dc["dc:coverage"], "United States of America, Virginia, Roanoke, Bennett Springs")
        self.assertEqual(dc["dc:description"], "")
        self.assertEqual(dc["dc:type"], "PhysicalObject")


@unittest.skipUnless(MANIFEST.exists(), "no manifest yet")
class Manifest(unittest.TestCase):
    """Phase 1 gate: 100 rows, 30/70 split, every image present, caps honored. Reads no field values beyond
    the cap keys, so it does not open the test split's labels."""

    def test_manifest(self):
        rows = load_manifest()
        self.assertEqual(len(rows), 100)
        self.assertEqual(len({r["gbifID"] for r in rows}), 100)
        self.assertEqual(Counter(r["split"] for r in rows), {"dev": 30, "test": 70})
        for r in rows:
            self.assertTrue(image_for(r["gbifID"]).exists(), r["gbifID"])
            self.assertTrue(r["recordedBy"] and r["eventDate"])
        caps = {"collector": Counter(collector_key(r["recordedBy"]) for r in rows),
                "family": Counter(r["family"] for r in rows),
                "decade": Counter(int(r["year"]) // 10 for r in rows)}
        for k, c in caps.items():
            self.assertLessEqual(max(c.values()), CAP[k], k)
        self.assertTrue(set(FIELDS) <= set(rows[0]))


if __name__ == "__main__":
    unittest.main()
