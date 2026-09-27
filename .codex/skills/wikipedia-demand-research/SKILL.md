---
name: wikipedia-demand-research
description: "Analyze Wikipedia pageview trends for a confirmed or clarifiable topic across language editions and create reproducible research reports. Use for first-pass topic-interest research; not for market sizing, willingness to pay, or audience estimates."
---

# Wikipedia Demand Research

Use this skill to produce a reproducible first-pass signal of interest in a
Wikipedia topic. The current implementation resolves one confirmed source
article—or a user-confirmed basket of articles—across up to five language
editions via Wikidata, compares article pageviews, and creates a chart plus a
one-page PDF report.

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
   user has not supplied an exact source article title, run `--search` with
   `--search-limit 4` against a suitable source edition. Show up to four
   candidates at once, each with title, QID, description, and any
   disambiguation marker; do not present only one "best" result. Say explicitly
   when fewer than four candidates are available, and let the user choose an
   offered article, provide another title, or refine the search. Do not run
   analysis, create `research.yaml`, or silently select an article until they
   confirm it.
2. Confirm the language editions, period, decision question, and what would
   make the result useful to the user. For a broader topic, ask the user to
   confirm every article in the basket. The default is
   separate analysis per article; never create an
   aggregate without explicit user approval.
   Keep the default traffic scope unless the user asks to compare a device
   type: `all-access` includes desktop, mobile web, and mobile app. Use
   `--access desktop`, `--access mobile-web`, or `--access mobile-app` only
   when that distinction matters to the user's question.
3. **Stop and wait for an explicit launch confirmation in a later user
   message.** A contact address or permission to use it as a Wikimedia
   `User-Agent` permits API identification only; it is not permission to begin
   research. Do not create `research.yaml`, download pageviews, or say that
   analysis is starting in the same turn that candidates, inputs, or contact
   permission are discussed. This gate applies even when the user initially
   supplied an exact article title. Require a clear instruction such as
   “Підтверджую статтю X, запускай аналіз.”
4. Run `.codex/skills/wikipedia-demand-research/scripts/compare_topic.py`. It retrieves the source page's Wikidata QID,
   finds matching articles in the requested editions, downloads pageviews, and
   writes a chart, report, data, and manifest to one output directory.
5. Before responding, inspect `research_manifest.json` to verify the requested
   inputs and resolved titles, then inspect `monthly_pageviews.csv` for
   completeness and trends. Use `report.pdf` and `chart.png` only after the
   manifest and CSV support the interpretation. If an edition has no linked
   article, report that gap rather than substituting a similar page.
6. Exclude incomplete months from key comparisons. Treat failed or empty API
   responses as missing data, not zero interest. Flag conspicuous single-month
   spikes instead of presenting them as sustained growth.
7. Give the PDF, CSV, manifest, and a cautious next research step. For each
   edition, distinguish the data observation, calculated confidence in that
   observation, and the user-confirmed relevance of the article proxy to the
   stated decision. Explain both the observed signal and its limitations.

## Saved research

When the user is likely to revise, repeat, or extend a confirmed study, create
and run a `research.yaml` specification rather than reconstructing command-line
parameters. Read [the saved-research guide](references/research-spec.md) for
the creation command, schema, and revision rules. Each configuration-based run
gets a separate output directory and copies the applied specification beside
its manifest.

## Reproducible data collection

Responses from Wikimedia are cached in `outputs/cache/` by default. Reuse the
cache for ordinary repeated runs, use `--refresh` only when fresh API data are
needed, and use `--offline` to verify that a saved study can be reproduced
without network access. Inspect the manifest's `requests` list when explaining
which API responses were reused or retrieved.

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
- The default API filter is Wikimedia `user` traffic. Traffic Wikimedia
  categorizes as `spider` or `automated` is excluded; do not describe this as
  a guarantee that every non-human request was detected.
- Compare both raw views and `share_of_project_views` where available. The
  latter is available only for complete calendar months, because a partial
  article month cannot be fairly divided by a full-project monthly total.
- Use the indexed chart to compare the direction and scale of change between
  editions of very different sizes. It starts each series at 100 for its first
  complete non-zero month; it does not show absolute interest.
- Do not call an observed pattern a forecast, statistically significant result,
  market demand, or proof that a product should be built.

Read [the methodology note](references/methodology.md) before interpreting the
data or explaining its limitations.

## Validation and further development

Before releasing a material change, follow the evidence and remaining test
case in the [validation record](references/validation.md). When explaining how
AI-assisted development was checked, use the
[development notes](references/development-notes.md). Read the
[roadmap](references/roadmap.md) only when planning an extension beyond the
current workflow.
