"""Read and write durable specifications for single-article research runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import re

import yaml


QID_PATTERN = re.compile(r"Q[1-9][0-9]*$")


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string.")
    return value.strip()


def _parse_date(value: object, field: str) -> date:
    text = _required_text(value, field)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(f"{field} must use YYYY-MM-DD.") from error


@dataclass(frozen=True)
class TopicArticle:
    source_project: str
    source_title: str
    qid: str
    role: str = "supporting"
    weight: float = 1.0
    label: str | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"source_project": self.source_project, "source_title": self.source_title, "qid": self.qid, "role": self.role, "weight": self.weight}
        if self.label:
            result["label"] = self.label
        return result


def _parse_article(payload: object) -> TopicArticle:
    if not isinstance(payload, dict):
        raise ValueError("topic.articles entries must be mappings.")
    qid = _required_text(payload.get("qid"), "topic.articles[].qid")
    if not QID_PATTERN.fullmatch(qid):
        raise ValueError("topic.articles[].qid must look like a Wikidata QID, for example Q1860.")
    role = payload.get("role", "supporting")
    if role not in {"primary", "supporting"}:
        raise ValueError("topic.articles[].role must be primary or supporting.")
    weight = payload.get("weight", 1.0)
    if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight <= 0:
        raise ValueError("topic.articles[].weight must be a positive number.")
    label = payload.get("label")
    return TopicArticle(_required_text(payload.get("source_project"), "topic.articles[].source_project"), _required_text(payload.get("source_title"), "topic.articles[].source_title"), qid, role, float(weight), _required_text(label, "topic.articles[].label") if label is not None else None)


@dataclass(frozen=True)
class ResearchSpec:
    """Confirmed inputs that define one reproducible research question."""

    research_name: str
    source_project: str
    source_title: str
    qid: str
    projects: tuple[str, ...]
    start: date
    end: date
    topic_label: str | None = None
    articles: tuple[TopicArticle, ...] = ()

    @property
    def topic_articles(self) -> tuple[TopicArticle, ...]:
        if self.articles:
            return self.articles
        return (TopicArticle(self.source_project, self.source_title, self.qid, "primary", 1.0, self.topic_label),)

    def to_dict(self) -> dict[str, object]:
        topic: dict[str, object] = {"articles": [article.to_dict() for article in self.topic_articles]}
        if self.topic_label:
            topic["label"] = self.topic_label
        return {
            "research_name": self.research_name,
            "topic": topic,
            "projects": list(self.projects),
            "period": {"start": self.start.isoformat(), "end": self.end.isoformat()},
        }


def parse_research_spec(payload: object) -> ResearchSpec:
    """Validate the supported portion of a research.yaml document."""

    if not isinstance(payload, dict):
        raise ValueError("research.yaml must contain a YAML mapping.")
    topic = payload.get("topic")
    period = payload.get("period")
    projects = payload.get("projects")
    if not isinstance(topic, dict):
        raise ValueError("topic must be a mapping.")
    if not isinstance(period, dict):
        raise ValueError("period must be a mapping.")
    if not isinstance(projects, list) or not projects:
        raise ValueError("projects must be a non-empty list of Wikipedia editions.")

    articles_payload = topic.get("articles")
    if articles_payload is None:
        articles_payload = [{"source_project": topic.get("source_project"), "source_title": topic.get("source_title"), "qid": topic.get("qid"), "label": topic.get("label"), "role": "primary"}]
    if not isinstance(articles_payload, list) or not articles_payload:
        raise ValueError("topic.articles must be a non-empty list.")
    articles = tuple(_parse_article(article) for article in articles_payload)
    if len({article.qid for article in articles}) != len(articles):
        raise ValueError("topic.articles must not contain duplicate QIDs.")
    if sum(article.role == "primary" for article in articles) != 1:
        raise ValueError("topic.articles must contain exactly one primary article.")
    primary = next(article for article in articles if article.role == "primary")
    validated_projects = tuple(_required_text(project, "projects[]") for project in projects)
    if len(set(validated_projects)) != len(validated_projects):
        raise ValueError("projects must not contain duplicate editions.")

    start = _parse_date(period.get("start"), "period.start")
    end = _parse_date(period.get("end"), "period.end")
    if end < start:
        raise ValueError("period.end must not be before period.start.")
    label = topic.get("label")
    if label is not None:
        label = _required_text(label, "topic.label")
    return ResearchSpec(
        research_name=_required_text(payload.get("research_name"), "research_name"),
        source_project=primary.source_project,
        source_title=primary.source_title,
        qid=primary.qid,
        projects=validated_projects,
        start=start,
        end=end,
        topic_label=label,
        articles=articles,
    )


def load_research_spec(path: Path) -> ResearchSpec:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"Could not read research specification {path}: {error}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"Could not parse research specification {path}: {error}") from error
    return parse_research_spec(payload)


def write_research_spec(path: Path, spec: ResearchSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(spec.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def default_run_output_dir(research_path: Path, now: datetime | None = None) -> Path:
    """Give each configuration-based run its own immutable output directory."""

    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return research_path.parent / "runs" / timestamp
