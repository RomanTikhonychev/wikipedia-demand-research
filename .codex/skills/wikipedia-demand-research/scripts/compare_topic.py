#!/usr/bin/env python3
"""Compare one Wikidata-linked topic across Wikipedia language editions."""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "wikipedia-demand-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from research_config import ResearchSpec, default_run_output_dir, load_research_spec, write_research_spec


REST_ROOT = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
USER_AGENT = ""


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use dates in YYYY-MM-DD format.") from error


def timestamp(value: date) -> str:
    return value.strftime("%Y%m%d00")


def get_json(url: str) -> dict:
    if not USER_AGENT:
        raise RuntimeError("Provide --user-agent with a contact URL or email before calling Wikimedia.")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"Request failed with HTTP {error.code}: {url}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Wikimedia: {error.reason}") from error


def mediawiki_api(project: str, params: dict[str, str]) -> dict:
    return get_json(f"https://{project}.org/w/api.php?{urlencode(params)}")


def resolve_source(project: str, title: str) -> tuple[str, str]:
    payload = mediawiki_api(
        project,
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
            "prop": "pageprops",
            "titles": title,
        },
    )
    pages = payload.get("query", {}).get("pages", [])
    if len(pages) != 1 or "missing" in pages[0]:
        raise RuntimeError(f"Could not find '{title}' in {project}.")
    qid = pages[0].get("pageprops", {}).get("wikibase_item")
    if not qid:
        raise RuntimeError(f"'{title}' in {project} has no Wikidata item to link across languages.")
    return qid, pages[0]["title"]


def search_candidates(project: str, query: str, limit: int) -> list[dict[str, object]]:
    payload = mediawiki_api(project, {"action": "query", "format": "json", "formatversion": "2", "generator": "search", "gsrsearch": query, "gsrlimit": str(limit), "prop": "pageprops|description"})
    candidates = []
    for page in payload.get("query", {}).get("pages", []):
        props = page.get("pageprops", {})
        candidates.append({"title": page["title"], "qid": props.get("wikibase_item"), "description": page.get("description"), "disambiguation": "disambiguation" in props})
    return candidates


def project_site(project: str) -> str:
    if not project.endswith(".wikipedia"):
        raise RuntimeError("Only language Wikipedia projects such as uk.wikipedia are supported.")
    language = project.removesuffix(".wikipedia")
    if not language or "." in language:
        raise RuntimeError(f"Invalid Wikipedia project: {project}")
    return f"{language}wiki"


def resolve_sitelinks(qid: str, projects: list[str]) -> dict[str, str]:
    url = "https://www.wikidata.org/w/api.php?" + urlencode(
        {"action": "wbgetentities", "format": "json", "ids": qid, "props": "sitelinks"}
    )
    entity = get_json(url).get("entities", {}).get(qid, {})
    sitelinks = entity.get("sitelinks", {})
    result = {}
    for project in projects:
        link = sitelinks.get(project_site(project))
        if link:
            result[project] = link["title"]
    return result


def article_url(project: str, article: str, start: date, end: date) -> str:
    encoded_article = quote(article.replace(" ", "_"), safe="")
    return f"{REST_ROOT}/per-article/{project}/all-access/user/{encoded_article}/daily/{timestamp(start)}/{timestamp(end)}"


def aggregate_url(project: str, start: date, end: date) -> str:
    return f"{REST_ROOT}/aggregate/{project}/all-access/user/monthly/{timestamp(start)}/{timestamp(end)}"


def article_daily(payload: dict) -> list[tuple[str, int]]:
    rows = []
    for item in payload.get("items", []):
        day = datetime.strptime(item["timestamp"][:8], "%Y%m%d").date().isoformat()
        rows.append((day, int(item["views"])))
    return sorted(rows)


def monthly_article(rows: list[tuple[str, int]], start: date, end: date) -> dict[str, dict[str, int]]:
    result: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"views": 0, "days": 0, "expected_days": 0, "zero_days": 0})
    current = start
    while current <= end:
        result[current.strftime("%Y-%m")]["expected_days"] += 1
        current = date.fromordinal(current.toordinal() + 1)
    for day, views in rows:
        month = day[:7]
        result[month]["views"] += views
        result[month]["days"] += 1
        if views == 0:
            result[month]["zero_days"] += 1
    for item in result.values():
        item["missing_days"] = item["expected_days"] - item["days"]
    return dict(result)


def project_monthly(payload: dict) -> dict[str, int]:
    return {
        datetime.strptime(item["timestamp"][:8], "%Y%m%d").strftime("%Y-%m"): int(item["views"])
        for item in payload.get("items", [])
    }


def is_complete_month(month: str, days: int, start: date, end: date) -> bool:
    year, number = map(int, month.split("-"))
    first = date(year, number, 1)
    last = date(year, number, calendar.monthrange(year, number)[1])
    return start <= first and end >= last and days == last.day


def percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:+.0f}%"


def metrics(rows: list[dict]) -> dict[str, object]:
    complete = [row for row in rows if row["complete_month"]]
    values = [row["article_views"] for row in complete]
    expected_days = sum(row.get("expected_days", 0) for row in rows)
    observed_days = sum(row.get("days_with_data", 0) for row in rows)
    coverage = observed_days / expected_days if expected_days else 0
    quality = {"complete_months": len(complete), "incomplete_months": len(rows) - len(complete), "expected_days": expected_days, "days_with_data": observed_days, "missing_days": sum(row.get("missing_days", 0) for row in rows), "zero_days": sum(row.get("zero_days", 0) for row in rows), "coverage": coverage}
    if len(values) < 6:
        return {
            "trend": "insufficient data",
            "period_change": None,
            "year_over_year": None,
            "reliability": "low",
            "reliability_reason": "Fewer than six complete calendar months are available.",
            "data_quality": quality,
        }
    window = min(3, len(values) // 2)
    baseline = sum(values[:window]) / window
    recent = sum(values[-window:]) / window
    change = (recent / baseline - 1) if baseline else None
    if change is None:
        trend = "insufficient data"
    elif change >= 0.15:
        trend = "growing"
    elif change <= -0.15:
        trend = "declining"
    else:
        trend = "roughly flat"
    yoy = None
    if len(values) >= 24:
        earlier = sum(values[-24:-12])
        later = sum(values[-12:])
        yoy = later / earlier - 1 if earlier else None
    reliability = "high" if len(values) >= 24 else "medium"
    reasons = [f"{len(values)} complete calendar months"]
    if coverage < 0.98:
        reliability = "medium" if reliability == "high" else "low"
        reasons.append(f"{coverage:.0%} daily data coverage")
    typical = median(values)
    if typical < 100:
        reliability = "low"
        reasons.append("very low typical traffic")
    if typical and max(values) > 3 * typical:
        reliability = "medium" if reliability == "high" else "low"
        reasons.append("one monthly spike exceeds three times the median")
    return {
        "trend": trend,
        "period_change": change,
        "year_over_year": yoy,
        "reliability": reliability,
        "reliability_reason": "; ".join(reasons) + ".",
        "data_quality": quality,
    }


def create_chart(series: dict[str, list[dict]], chart_path: Path) -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    figure, (raw_axis, share_axis) = plt.subplots(1, 2, figsize=(10, 3.5), dpi=180)
    for project, rows in series.items():
        months = [row["month"] for row in rows]
        raw_axis.plot(
            months,
            [row["article_views"] for row in rows],
            marker="o",
            markersize=2.5,
            linewidth=1.7,
            label=project,
        )
        shares = [row["share_of_project_views"] * 1_000_000 if row["share_of_project_views"] is not None else float("nan") for row in rows]
        share_axis.plot(months, shares, marker="o", markersize=2.5, linewidth=1.7, label=project)
    raw_axis.set_title("Monthly article views")
    raw_axis.set_ylabel("views")
    share_axis.set_title("Article share of edition views")
    share_axis.set_ylabel("views per million")
    for axis in (raw_axis, share_axis):
        axis.tick_params(axis="x", rotation=35, labelsize=7)
        axis.grid(axis="y", alpha=0.2)
    raw_axis.legend(frameon=False, fontsize=7, ncol=min(2, len(series)))
    figure.tight_layout()
    figure.savefig(chart_path, bbox_inches="tight")
    plt.close(figure)


def create_pdf(
    path: Path,
    chart_path: Path,
    topic: str,
    qid: str,
    summary: dict[str, dict],
    start: date,
    end: date,
    missing_projects: list[str],
) -> None:
    font_path = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
    pdfmetrics.registerFont(TTFont("DejaVu", str(font_path)))
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="DejaVu", fontSize=8, leading=10)
    heading = ParagraphStyle(
        "Heading",
        parent=styles["Heading1"],
        fontName="DejaVu",
        fontSize=14,
        leading=16,
        alignment=0,
        wordWrap="CJK",
    )
    document = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm
    )
    story = [Paragraph(f"Wikipedia interest signal: {topic}", heading)]
    story.append(Paragraph(f"Wikidata item: {qid}. Period: {start.isoformat()} to {end.isoformat()}.", body))
    story.append(Spacer(1, 3 * mm))
    image = Image(str(chart_path), width=178 * mm, height=62 * mm)
    story.extend([image, Spacer(1, 3 * mm)])
    table_rows = [["Edition", "Article", "Trend", "Change", "YoY", "Reliability"]]
    for project, item in summary.items():
        table_rows.append(
            [project, item["article"], item["trend"], percent(item["period_change"]), percent(item["year_over_year"]), item["reliability"]]
        )
    table = Table(table_rows, colWidths=[28 * mm, 46 * mm, 28 * mm, 18 * mm, 18 * mm, 28 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF8")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D4E5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.extend([table, Spacer(1, 3 * mm)])
    bullets = []
    for project, item in summary.items():
        bullets.append(f"{project}: {item['trend']} ({percent(item['period_change'])}); {item['reliability_reason']}")
    story.append(Paragraph("<br/>".join(bullets), body))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            "Interpretation limit: article pageviews are a topic-interest signal, not market size, unique people, willingness to pay, or proof of product demand.",
            body,
        )
    )
    if missing_projects:
        story.append(Paragraph(f"No Wikidata-linked article was found for: {', '.join(missing_projects)}.", body))
    story.append(Paragraph("Source: Wikimedia Pageviews API. Exact requests and resolved articles are in research_manifest.json.", body))
    document.build(story)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare a Wikidata-linked topic across Wikipedia language editions.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--research", type=Path, help="Run a saved research.yaml specification")
    mode.add_argument("--init-research", type=Path, help="Create a confirmed research.yaml specification from the supplied topic")
    mode.add_argument("--search", help="Search candidate Wikipedia articles; does not create or run research")
    parser.add_argument("--research-name", help="Name stored in --init-research; defaults to the source article title")
    parser.add_argument("--source-project", help="Edition containing --topic, e.g. en.wikipedia")
    parser.add_argument("--search-limit", type=int, default=5, help="Maximum candidates for --search (1-10)")
    parser.add_argument("--topic", help="Exact source article title")
    parser.add_argument("--projects", help="Comma-separated editions, e.g. pl.wikipedia,cs.wikipedia")
    parser.add_argument("--start", type=parse_date, help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end", type=parse_date, help="Inclusive YYYY-MM-DD")
    parser.add_argument("--output-dir", type=Path, help="Output directory; required for direct runs and optional for --research")
    parser.add_argument(
        "--user-agent",
        default=os.environ.get("WIKIMEDIA_USER_AGENT"),
        help="Required Wikimedia client identifier with a contact URL or email; may be set via WIKIMEDIA_USER_AGENT",
    )
    return parser.parse_args()


def direct_run_spec(args: argparse.Namespace) -> ResearchSpec:
    required = {
        "--source-project": args.source_project,
        "--topic": args.topic,
        "--projects": args.projects,
        "--start": args.start,
        "--end": args.end,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError(f"Direct runs require {', '.join(missing)}.")
    projects = tuple(dict.fromkeys([args.source_project, *[project.strip() for project in args.projects.split(",") if project.strip()]]))
    return ResearchSpec(
        research_name=args.research_name or args.topic,
        source_project=args.source_project,
        source_title=args.topic,
        qid="Q1",
        projects=projects,
        start=args.start,
        end=args.end,
    )


def validate_run(spec: ResearchSpec) -> None:
    if spec.end > date.today():
        raise ValueError("Choose a non-future date range where period.end is not after today.")
    if len(spec.projects) > 5:
        raise ValueError("Use no more than five editions in one report.")
    for project in spec.projects:
        project_site(project)


def copy_research_spec(research_path: Path | None, output_dir: Path) -> str | None:
    if research_path is None:
        return None
    snapshot = output_dir / "research.yaml"
    if research_path.resolve() != snapshot.resolve():
        shutil.copyfile(research_path, snapshot)
    return snapshot.name


def run_article_basket(args: argparse.Namespace, spec: ResearchSpec, output_dir: Path) -> int:
    """Run each confirmed proxy separately; no implicit aggregate is created."""

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, article in enumerate(spec.topic_articles, start=1):
        resolved_qid, canonical_title = resolve_source(article.source_project, article.source_title)
        if resolved_qid != article.qid:
            print(
                f"Error: {article.source_title} now resolves to {resolved_qid}, but research.yaml declares {article.qid}. "
                "Confirm the intended article before updating the specification.",
                file=sys.stderr,
            )
            return 1
        article_dir = output_dir / f"{index:02d}-{article.qid}"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--source-project", article.source_project,
            "--topic", canonical_title,
            "--projects", ",".join(spec.projects),
            "--start", spec.start.isoformat(),
            "--end", spec.end.isoformat(),
            "--output-dir", str(article_dir),
            "--user-agent", args.user_agent,
        ]
        completed = subprocess.run(command, check=False)
        if completed.returncode:
            return completed.returncode
        shutil.copyfile(args.research, article_dir / "research.yaml")
        results.append({"qid": article.qid, "role": article.role, "weight": article.weight, "source_title": canonical_title, "output_dir": article_dir.name})
    (output_dir / "research_manifest.json").write_text(
        json.dumps({"created_at": datetime.now(timezone.utc).isoformat(), "research_spec_file": "research.yaml", "aggregation": "none", "articles": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(args.research, output_dir / "research.yaml")
    print(f"Created separate article reports in {output_dir}")
    return 0


def main() -> int:
    global USER_AGENT
    args = parse_args()
    if not args.user_agent:
        print("Error: provide --user-agent or set WIKIMEDIA_USER_AGENT with contact information.", file=sys.stderr)
        return 2
    USER_AGENT = args.user_agent
    try:
        if args.search:
            if not args.source_project:
                raise ValueError("--search requires --source-project.")
            if not 1 <= args.search_limit <= 10:
                raise ValueError("--search-limit must be between 1 and 10.")
            print(json.dumps(search_candidates(args.source_project, args.search, args.search_limit), ensure_ascii=False, indent=2))
            return 0
        if args.init_research and args.output_dir is not None:
            raise ValueError("--init-research does not create a report; omit --output-dir and run the saved specification next.")
        if args.research:
            if any(value is not None for value in (args.source_project, args.topic, args.projects, args.start, args.end, args.research_name)):
                raise ValueError("Use either --research or direct topic parameters, not both.")
            spec = load_research_spec(args.research)
            research_path: Path | None = args.research
            output_dir = args.output_dir or default_run_output_dir(args.research)
            if len(spec.topic_articles) > 1:
                validate_run(spec)
                return run_article_basket(args, spec, output_dir)
        else:
            spec = direct_run_spec(args)
            research_path = None
            if args.init_research:
                output_dir = None
            elif args.output_dir is None:
                raise ValueError("Direct runs require --output-dir.")
            else:
                output_dir = args.output_dir
        validate_run(spec)
        qid, canonical_source_title = resolve_source(spec.source_project, spec.source_title)
        if args.init_research:
            initialized_spec = ResearchSpec(
                research_name=args.research_name or canonical_source_title,
                source_project=spec.source_project,
                source_title=canonical_source_title,
                qid=qid,
                projects=spec.projects,
                start=spec.start,
                end=spec.end,
            )
            write_research_spec(args.init_research, initialized_spec)
            print(f"Created confirmed research specification in {args.init_research}")
            return 0
        if args.research and qid != spec.qid:
            raise RuntimeError(
                f"The source article now resolves to {qid}, but research.yaml declares {spec.qid}. "
                "Confirm the intended article before updating the specification."
            )
        titles = resolve_sitelinks(qid, list(spec.projects))
        titles[spec.source_project] = canonical_source_title
        missing_projects = [project for project in spec.projects if project not in titles]
        if not titles:
            raise RuntimeError("No language-linked articles were found.")
        raw: dict[str, dict] = {"article_pageviews": {}, "project_pageviews": {}}
        all_rows: list[dict] = []
        series: dict[str, list[dict]] = {}
        summary: dict[str, dict] = {}
        for project, article in titles.items():
            this_article_url = article_url(project, article, spec.start, spec.end)
            this_aggregate_url = aggregate_url(project, spec.start, spec.end)
            article_payload = get_json(this_article_url)
            project_payload = get_json(this_aggregate_url)
            raw["article_pageviews"][project] = article_payload
            raw["project_pageviews"][project] = project_payload
            raw.setdefault("source_urls", {})[project] = {
                "article_pageviews": this_article_url,
                "project_pageviews": this_aggregate_url,
            }
            article_months = monthly_article(article_daily(article_payload), spec.start, spec.end)
            totals = project_monthly(project_payload)
            rows = []
            for month, item in sorted(article_months.items()):
                complete = is_complete_month(month, item["days"], spec.start, spec.end)
                project_views = totals.get(month)
                share = item["views"] / project_views if complete and project_views else None
                rows.append(
                    {"project": project, "article": article, "month": month, "article_views": item["views"], "days_with_data": item["days"], "expected_days": item["expected_days"], "missing_days": item["missing_days"], "zero_days": item["zero_days"], "complete_month": complete, "project_views": project_views, "share_of_project_views": share}
                )
            series[project] = rows
            item_summary = metrics(rows)
            summary[project] = {"article": article, **item_summary}
            all_rows.extend(rows)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    assert output_dir is not None
    output_dir.mkdir(parents=True, exist_ok=True)
    research_snapshot = copy_research_spec(research_path, output_dir)
    with (output_dir / "monthly_pageviews.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    chart_path = output_dir / "chart.png"
    create_chart(series, chart_path)
    create_pdf(
        output_dir / "report.pdf",
        chart_path,
        canonical_source_title,
        qid,
        summary,
        spec.start,
        spec.end,
        missing_projects,
    )
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {"source_project": spec.source_project, "topic": spec.source_title, "projects": list(spec.projects), "start": spec.start.isoformat(), "end": spec.end.isoformat()},
        "wikidata_qid": qid,
        "resolved_articles": titles,
        "projects_without_linked_article": missing_projects,
        "summary": summary,
        "raw_data_file": "raw_pageviews.json",
        "methodology_version": "0.1",
    }
    if research_snapshot:
        manifest["research_spec_file"] = research_snapshot
    (output_dir / "research_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "raw_pageviews.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created report, chart, data, and manifest in {output_dir}")
    if missing_projects:
        print("No Wikidata-linked article found for: " + ", ".join(missing_projects), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
