import importlib.util
import json
import subprocess
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


COMPARE_PATH = Path(__file__).parents[1] / "scripts" / "compare_topic.py"
SCRIPTS_PATH = COMPARE_PATH.parent
FIXTURES_PATH = Path(__file__).parent / "fixtures"
EXAMPLES_PATH = Path(__file__).parents[1] / "examples"
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

    def test_access_specific_urls_keep_user_traffic_filter(self):
        article = compare_topic.article_url("uk.wikipedia", "Astronomy", date(2024, 1, 1), date(2024, 1, 31), "mobile-web")
        aggregate = compare_topic.aggregate_url("uk.wikipedia", date(2024, 1, 1), date(2024, 1, 31), "desktop")
        self.assertIn("/mobile-web/user/Astronomy/", article)
        self.assertIn("/desktop/user/monthly/", aggregate)

    def test_traffic_metadata_records_excluded_categories(self):
        self.assertEqual(
            compare_topic.traffic_metadata("mobile-app"),
            {"access": "mobile-app", "access_label": "mobile app", "agent": "user", "excluded_agent_categories": ["spider", "automated"]},
        )

    def test_search_returns_up_to_four_candidates_by_default(self):
        payload = {
            "query": {
                "pages": [
                    {"title": "On-board diagnostics", "pageprops": {"wikibase_item": "Q1"}, "description": "vehicle diagnostics"},
                    {"title": "ELM327", "pageprops": {"wikibase_item": "Q2"}, "description": "adapter"},
                    {"title": "OBD-II PIDs", "pageprops": {"wikibase_item": "Q3"}, "description": "diagnostic parameters"},
                    {"title": "OBD", "pageprops": {"wikibase_item": "Q4", "disambiguation": ""}, "description": "disambiguation page"},
                ]
            }
        }
        with patch.object(compare_topic, "mediawiki_api", return_value=payload) as request:
            candidates = compare_topic.search_candidates("en.wikipedia", "OBD adapter", 4)
        self.assertEqual(len(candidates), 4)
        self.assertEqual(request.call_args.args[1]["gsrlimit"], "4")
        self.assertTrue(candidates[-1]["disambiguation"])

    def test_search_limit_defaults_to_four(self):
        with patch.object(sys, "argv", ["compare_topic.py", "--search", "OBD adapter", "--source-project", "en.wikipedia"]):
            self.assertEqual(compare_topic.parse_args().search_limit, 4)

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

    def test_pageview_fixture_preserves_a_gap_and_zero_day(self):
        payload = json.loads((FIXTURES_PATH / "article_pageviews_with_gap.json").read_text(encoding="utf-8"))
        result = compare_topic.monthly_article(compare_topic.article_daily(payload), date(2024, 2, 1), date(2024, 2, 3))
        self.assertEqual(result["2024-02"], {"views": 12, "days": 2, "expected_days": 3, "zero_days": 1, "missing_days": 1})

    def test_get_json_uses_cached_response_in_offline_mode(self):
        with TemporaryDirectory() as temporary_directory:
            cache_dir = Path(temporary_directory)
            url = "https://example.test/data"
            key = __import__("hashlib").sha256(url.encode("utf-8")).hexdigest()
            (cache_dir / f"{key}.json").write_text(json.dumps({"url": url, "retrieved_at": "2026-09-27T00:00:00+00:00", "payload": {"items": []}}), encoding="utf-8")
            previous = compare_topic.CACHE_DIR, compare_topic.OFFLINE, compare_topic.REFRESH, compare_topic.USER_AGENT
            try:
                compare_topic.CACHE_DIR, compare_topic.OFFLINE, compare_topic.REFRESH, compare_topic.USER_AGENT = cache_dir, True, False, "test/1 (test@example.com)"
                self.assertEqual(compare_topic.get_json(url), {"items": []})
            finally:
                compare_topic.CACHE_DIR, compare_topic.OFFLINE, compare_topic.REFRESH, compare_topic.USER_AGENT = previous

    def test_markdown_report_includes_quality_and_limits(self):
        summary = {"uk.wikipedia": {"article": "Astronomy", "trend": "growing", "period_change": 0.2, "reliability": "medium", "reliability_reason": "12 complete calendar months.", "data_quality": {"coverage": 1.0, "days_with_data": 365, "expected_days": 365}}}
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "report.md"
            compare_topic.create_markdown_report(path, "Astronomy", "Q6999", summary, date(2024, 1, 1), date(2024, 12, 31), [])
            text = path.read_text(encoding="utf-8")
            self.assertIn("Coverage", text)
            self.assertIn("not market size", text)
            self.assertIn("spider or automated is excluded", text)

    def test_decision_conclusion_separates_data_confidence_and_relevance(self):
        item = {
            "trend": "growing",
            "period_change": 0.2,
            "reliability": "medium",
            "reliability_reason": "12 complete calendar months.",
        }
        conclusion = compare_topic.conclusion_for_edition(
            "uk.wikipedia",
            item,
            "Should we validate an astronomy course for Ukrainian readers?",
            "medium",
            "Article views show topic interest, not course intent.",
        )
        self.assertIn("increased by +20%", conclusion["data_observation"])
        self.assertEqual(conclusion["confidence"], "medium")
        self.assertEqual(conclusion["decision_relevance"]["assessment"], "medium")
        self.assertIn("not course intent", compare_topic.conclusion_text(conclusion))

    def test_markdown_report_includes_decision_conclusion(self):
        summary = {"uk.wikipedia": {"article": "Astronomy", "trend": "growing", "period_change": 0.2, "reliability": "medium", "reliability_reason": "12 complete calendar months.", "data_quality": {"coverage": 1.0, "days_with_data": 365, "expected_days": 365}}}
        conclusion = compare_topic.conclusion_for_edition("uk.wikipedia", summary["uk.wikipedia"])
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "report.md"
            compare_topic.create_markdown_report(path, "Astronomy", "Q6999", summary, date(2024, 1, 1), date(2024, 12, 31), [], conclusions=[conclusion])
            text = path.read_text(encoding="utf-8")
            self.assertIn("## Decision conclusions", text)
            self.assertIn("Decision relevance: not assessed", text)

    def test_pdf_is_one_page_and_contains_quality_table(self):
        summary = {"uk.wikipedia": {"article": "Astronomy", "trend": "growing", "period_change": 0.2, "year_over_year": None, "reliability": "medium", "reliability_reason": "12 complete calendar months.", "data_quality": {"coverage": 1.0, "missing_days": 0, "zero_days": 0}}}
        rows = [{"month": "2024-01", "article_views": 100, "share_of_project_views": 0.000001}]
        conclusion = compare_topic.conclusion_for_edition("uk.wikipedia", summary["uk.wikipedia"])
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            chart, pdf = root / "chart.png", root / "report.pdf"
            compare_topic.create_chart({"uk.wikipedia": rows}, chart)
            compare_topic.create_pdf(pdf, chart, "Astronomy", "Q6999", summary, date(2024, 1, 1), date(2024, 12, 31), [], "mobile-web", [conclusion])
            info = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout
            self.assertIn("Pages:           1", info)
            self.assertIn(b"%PDF", pdf.read_bytes()[:8])

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

    def test_indexed_views_uses_first_complete_nonzero_month(self):
        rows = [
            {"article_views": 200, "complete_month": False},
            {"article_views": 0, "complete_month": True},
            {"article_views": 80, "complete_month": True},
            {"article_views": 120, "complete_month": True},
            {"article_views": 160, "complete_month": False},
        ]
        self.assertEqual(compare_topic.indexed_views(rows), [None, None, 100.0, 150.0, None])

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

    def test_packaged_example_accepts_yaml_date_scalars(self):
        spec = research_config.load_research_spec(EXAMPLES_PATH / "research.yaml")
        self.assertEqual(spec.qid, "Q1860")
        self.assertEqual(spec.start, date(2024, 1, 1))
        self.assertEqual(spec.end, date(2024, 12, 31))

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

    def test_research_spec_defaults_to_all_access_and_accepts_mobile_web(self):
        payload = {
            "research_name": "traffic-scope",
            "topic": {"source_project": "en.wikipedia", "source_title": "English language", "qid": "Q1860"},
            "projects": ["uk.wikipedia"],
            "period": {"start": "2024-01-01", "end": "2024-12-31"},
        }
        self.assertEqual(research_config.parse_research_spec(payload).access, "all-access")
        payload["traffic"] = {"access": "mobile-web"}
        self.assertEqual(research_config.parse_research_spec(payload).access, "mobile-web")

    def test_research_spec_preserves_decision_context_and_relevance(self):
        payload = {
            "research_name": "decision-context",
            "topic": {"source_project": "en.wikipedia", "source_title": "English language", "qid": "Q1860"},
            "projects": ["uk.wikipedia"],
            "period": {"start": "2024-01-01", "end": "2024-12-31"},
            "decision": {
                "question": "Which audience should we validate next?",
                "proxy_relevance": "medium",
                "proxy_relevance_reason": "Topic interest is not purchase intent.",
            },
        }
        spec = research_config.parse_research_spec(payload)
        self.assertEqual(spec.decision_question, "Which audience should we validate next?")
        self.assertEqual(spec.proxy_relevance, "medium")
        self.assertEqual(spec.to_dict()["decision"], payload["decision"])

    def test_research_spec_requires_a_question_for_proxy_relevance(self):
        payload = {
            "research_name": "missing-question",
            "topic": {"source_project": "en.wikipedia", "source_title": "English language", "qid": "Q1860"},
            "projects": ["uk.wikipedia"],
            "period": {"start": "2024-01-01", "end": "2024-12-31"},
            "decision": {"proxy_relevance": "high"},
        }
        with self.assertRaisesRegex(ValueError, "requires decision.question"):
            research_config.parse_research_spec(payload)

    def test_access_option_is_available_without_changing_default(self):
        with patch.object(sys, "argv", ["compare_topic.py", "--source-project", "en.wikipedia", "--topic", "Astronomy", "--projects", "uk.wikipedia", "--start", "2024-01-01", "--end", "2024-12-31", "--output-dir", "outputs/example", "--access", "mobile-app"]):
            self.assertEqual(compare_topic.parse_args().access, "mobile-app")
        with patch.object(sys, "argv", ["compare_topic.py", "--source-project", "en.wikipedia", "--topic", "Astronomy", "--projects", "uk.wikipedia", "--start", "2024-01-01", "--end", "2024-12-31", "--output-dir", "outputs/example"]):
            self.assertEqual(compare_topic.direct_run_spec(compare_topic.parse_args()).access, "all-access")

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
