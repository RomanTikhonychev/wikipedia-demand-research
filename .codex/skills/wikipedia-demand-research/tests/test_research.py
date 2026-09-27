import importlib.util
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


COMPARE_PATH = Path(__file__).parents[1] / "scripts" / "compare_topic.py"
SCRIPTS_PATH = COMPARE_PATH.parent
import sys

sys.path.insert(0, str(SCRIPTS_PATH))
COMPARE_SPEC = importlib.util.spec_from_file_location("compare_topic", COMPARE_PATH)
compare_topic = importlib.util.module_from_spec(COMPARE_SPEC)
assert COMPARE_SPEC and COMPARE_SPEC.loader
COMPARE_SPEC.loader.exec_module(compare_topic)
import research_config


class ResearchTests(unittest.TestCase):
    def test_article_url_encodes_article_title(self):
        url = compare_topic.article_url(
            "uk.wikipedia", "Інтервальне голодування", date(2024, 1, 1), date(2024, 1, 31)
        )
        self.assertIn("/uk.wikipedia/all-access/user/", url)
        self.assertIn("%D0%86%D0%BD%D1%82", url)
        self.assertTrue(url.endswith("/2024010100/2024013100"))

    def test_monthly_article_tracks_views_and_days(self):
        rows = [("2024-01-30", 10), ("2024-01-31", 20), ("2024-02-01", 5)]
        self.assertEqual(
            compare_topic.monthly_article(rows, date(2024, 1, 30), date(2024, 2, 1)),
            {"2024-01": {"views": 30, "days": 2, "expected_days": 2, "zero_days": 0, "missing_days": 0}, "2024-02": {"views": 5, "days": 1, "expected_days": 1, "zero_days": 0, "missing_days": 0}},
        )

    def test_monthly_article_does_not_treat_missing_days_as_zero(self):
        result = compare_topic.monthly_article([("2024-02-01", 0)], date(2024, 2, 1), date(2024, 2, 3))
        self.assertEqual(result["2024-02"]["zero_days"], 1)
        self.assertEqual(result["2024-02"]["missing_days"], 2)

    def test_complete_month_requires_every_day_and_full_requested_month(self):
        self.assertTrue(compare_topic.is_complete_month("2024-02", 29, date(2024, 1, 1), date(2024, 3, 31)))
        self.assertFalse(compare_topic.is_complete_month("2024-02", 28, date(2024, 1, 1), date(2024, 3, 31)))
        self.assertFalse(compare_topic.is_complete_month("2024-02", 29, date(2024, 2, 2), date(2024, 3, 31)))

    def test_metrics_marks_short_series_low_reliability(self):
        rows = [
            {"complete_month": True, "article_views": 100, "month": f"2024-0{i}"}
            for i in range(1, 6)
        ]
        result = compare_topic.metrics(rows)
        self.assertEqual(result["trend"], "insufficient data")
        self.assertEqual(result["reliability"], "low")

    def test_research_spec_round_trip_preserves_confirmed_topic(self):
        spec = research_config.ResearchSpec(
            research_name="english-learning-de-uk",
            source_project="en.wikipedia",
            source_title="English language",
            qid="Q1860",
            projects=("en.wikipedia", "de.wikipedia", "uk.wikipedia"),
            start=date(2024, 1, 1),
            end=date(2025, 12, 31),
            topic_label="Learning English",
            articles=(research_config.TopicArticle("en.wikipedia", "English language", "Q1860", "primary", 1.0, "Learning English"),),
        )
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "research.yaml"
            research_config.write_research_spec(path, spec)
            self.assertEqual(research_config.load_research_spec(path), spec)

    def test_research_spec_rejects_missing_confirmed_qid(self):
        payload = {
            "research_name": "missing-qid",
            "topic": {"source_project": "en.wikipedia", "source_title": "English language"},
            "projects": ["uk.wikipedia"],
            "period": {"start": "2024-01-01", "end": "2024-12-31"},
        }
        with self.assertRaisesRegex(ValueError, r"topic.articles\[\].qid"):
            research_config.parse_research_spec(payload)

    def test_research_spec_accepts_a_primary_and_supporting_articles(self):
        spec = research_config.parse_research_spec({
            "research_name": "language-learning",
            "topic": {"articles": [
                {"source_project": "en.wikipedia", "source_title": "English language", "qid": "Q1860", "role": "primary"},
                {"source_project": "en.wikipedia", "source_title": "Second-language acquisition", "qid": "Q8162", "role": "supporting", "weight": 0.5},
            ]},
            "projects": ["de.wikipedia", "uk.wikipedia"],
            "period": {"start": "2024-01-01", "end": "2024-12-31"},
        })
        self.assertEqual([article.qid for article in spec.topic_articles], ["Q1860", "Q8162"])

    def test_research_spec_allows_source_edition_outside_target_projects(self):
        payload = {
            "research_name": "source-edition",
            "topic": {"source_project": "en.wikipedia", "source_title": "English language", "qid": "Q1860"},
            "projects": ["uk.wikipedia"],
            "period": {"start": "2024-01-01", "end": "2024-12-31"},
        }
        self.assertEqual(research_config.parse_research_spec(payload).projects, ("uk.wikipedia",))

    def test_default_output_directory_is_unique_per_run_timestamp(self):
        path = Path("researches") / "english-learning" / "research.yaml"
        now = datetime(2026, 9, 27, 8, 30, tzinfo=timezone.utc)
        self.assertEqual(
            research_config.default_run_output_dir(path, now),
            Path("researches") / "english-learning" / "runs" / "20260927T083000Z",
        )

    def test_configured_run_copies_the_applied_specification(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            research_path = root / "research.yaml"
            research_path.write_text("research_name: example\n", encoding="utf-8")
            output_dir = root / "runs" / "20260927T083000Z"
            output_dir.mkdir(parents=True)
            self.assertEqual(compare_topic.copy_research_spec(research_path, output_dir), "research.yaml")
            self.assertEqual((output_dir / "research.yaml").read_text(encoding="utf-8"), "research_name: example\n")


if __name__ == "__main__":
    unittest.main()
