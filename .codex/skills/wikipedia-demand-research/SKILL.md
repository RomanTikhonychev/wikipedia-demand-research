---
name: wikipedia-demand-research
description: "Analyze Wikipedia pageview trends for a confirmed or clarifiable topic across language editions and create reproducible research reports. Use for first-pass topic-interest research; not for market sizing, willingness to pay, or audience estimates."
---

# Wikipedia Demand Research

Use this skill to produce a reproducible first-pass signal of interest in a
Wikipedia topic. The current implementation resolves one confirmed source
article across up to five language editions via Wikidata, compares article
pageviews, and creates a chart plus a one-page PDF report.

When developing or substantially changing this skill, read the
[task requirements](references/task-requirements.md) and keep the result
self-contained within this skill directory.

## When to use it

Use this skill when the user wants to explore whether interest in a topic is
stable, changing, or relatively stronger in particular Wikipedia language
editions, and a Wikipedia article can serve as an agreed proxy. It can support
decisions about:

- which topics warrant further product research;
- which language audiences warrant further investigation; and
- whether the available pageview history is sufficient for a careful
  topic-interest conclusion.

Do not use it as a substitute for market sizing, pricing research, audience
measurement, country-level demand analysis, or a conclusion about willingness
to pay. Use another research approach when those are the user's primary
question.

## Research contract

The result measures views of named Wikipedia articles, their change over time,
and, for complete calendar months, their relative share of views within a
specific language edition. It does not measure unique people, market size,
product demand, willingness to pay, population, or the market of a country
associated with a language.

Treat a language edition as a language-based audience signal, not as a country
or market. The permitted conclusion is about the linked Wikipedia topic and
the available data, for example: “there is a signal for further validation,”
“interest in the related Wikipedia topic increased,” or “the data are
insufficient for a reliable conclusion.”

## Workflow

1. Understand the user's decision and identify the topic article proxy. If the
   user has not supplied an exact source article title, run `--search` against
   a suitable source edition, show the candidates (including QID and any
   disambiguation marker), and ask the user to choose. Do not run analysis,
   create `research.yaml`, or silently select an article until they confirm it.
2. Confirm the language editions, period, and what would make the result useful
   to the user. The current implementation accepts one article proxy; do not
   for a broader topic, ask the user to confirm every article in the basket.
   The default is separate analysis per article; never create an aggregate
   without explicit user approval.
3. Run `.codex/skills/wikipedia-demand-research/scripts/compare_topic.py`. It retrieves the source page's Wikidata QID,
   finds matching articles in the requested editions, downloads pageviews, and
   writes a chart, report, data, and manifest to one output directory.
4. Before responding, inspect `research_manifest.json` to verify the requested
   inputs and resolved titles, then inspect `monthly_pageviews.csv` for
   completeness and trends. Use `report.pdf` and `chart.png` only after the
   manifest and CSV support the interpretation. If an edition has no linked
   article, report that gap rather than substituting a similar page.
5. Exclude incomplete months from key comparisons. Treat failed or empty API
   responses as missing data, not zero interest. Flag conspicuous single-month
   spikes instead of presenting them as sustained growth.
6. Give the PDF, CSV, manifest, and a cautious next research step. Explain both
   the observed signal and its limitations.

## Saved research

When the user is likely to revise, repeat, or extend a confirmed study, create
and run a `research.yaml` specification rather than reconstructing command-line
parameters. Read [the saved-research guide](references/research-spec.md) for
the creation command, schema, and revision rules. Each configuration-based run
gets a separate output directory and copies the applied specification beside
its manifest.

## Command

```bash
.venv/bin/python .codex/skills/wikipedia-demand-research/scripts/compare_topic.py \
  --source-project en.wikipedia \
  --topic "Intermittent fasting" \
  --projects pl.wikipedia,cs.wikipedia,uk.wikipedia \
  --start 2024-01-01 \
  --end 2025-12-31 \
  --user-agent "my-research-skill/0.1 (contact@example.com)" \
  --output-dir outputs/intermittent-fasting-comparison
```

Prepare the environment once:

```bash
python3 -m venv .venv
.venv/bin/pip install -r .codex/skills/wikipedia-demand-research/requirements.txt
```

Commands assume that the current directory is the repository root. The script
writes `report.pdf`, `chart.png`, `monthly_pageviews.csv`,
`research_manifest.json`, and raw API data. Preserve these files with the final
analysis so the result can be checked or extended later.

Replace the example contact in `--user-agent` with a real contact URL or email,
or set it once as the `WIKIMEDIA_USER_AGENT` environment variable.

## Guardrails

- Do not silently substitute an article, invent a title, or treat a related
  article as the user's intended concept.
- A failed or empty API response is not proof of zero interest.
- Compare both raw views and `share_of_project_views` where available. The
  latter is available only for complete calendar months, because a partial
  article month cannot be fairly divided by a full-project monthly total.
- Do not call an observed pattern a forecast, statistically significant result,
  market demand, or proof that a product should be built.

Read [the methodology note](references/methodology.md) before interpreting the
data or explaining its limitations.
