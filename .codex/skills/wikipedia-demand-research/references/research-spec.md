# Saved research specification

Use a `research.yaml` file when a user may revise, repeat, or extend a
confirmed study. It can name either one article or a user-confirmed basket.
The specification is the durable statement of what was measured; each run
stores a copy beside its manifest and data.

## Create a specification

After the user confirms the exact source article, create the file with the
same topic, editions, and dates that a direct run would use:

```bash
.venv/bin/python .codex/skills/wikipedia-demand-research/scripts/compare_topic.py \
  --init-research researches/english-learning/research.yaml \
  --research-name "English learning: Germany and Ukraine" \
  --source-project en.wikipedia \
  --topic "English language" \
  --projects en.wikipedia,de.wikipedia,uk.wikipedia \
  --start 2024-01-01 \
  --end 2025-12-31 \
  --user-agent "my-research-skill/0.1 (contact@example.com)"
```

The command resolves and writes the canonical source title and its Wikidata
QID. This is the confirmation record: do not invent or manually replace the
QID when changing the topic.

## Run or revise a study

To repeat a study, run its saved configuration:

```bash
.venv/bin/python .codex/skills/wikipedia-demand-research/scripts/compare_topic.py \
  --research researches/english-learning/research.yaml \
  --user-agent "my-research-skill/0.1 (contact@example.com)"
```

Without `--output-dir`, the run is written to a new UTC-timestamped directory
under `researches/english-learning/runs/`. This preserves previous results.
Use `--output-dir` only when the user deliberately wants a particular output
location.

For a request such as “add French and update the period,” edit `projects` and
`period` in the existing file, then run it again. Preserve the confirmed
`topic` fields. At run time, the skill checks that the source title still
resolves to the saved QID; it stops for confirmation if it does not.

## Supported schema

```yaml
research_name: English learning: Germany and Ukraine
topic:
  label: Learning English # optional label for people
  source_project: en.wikipedia
  source_title: English language
  qid: Q1860
projects:
  - en.wikipedia
  - de.wikipedia
  - uk.wikipedia
period:
  start: 2024-01-01
  end: 2025-12-31
```

`projects` must be non-empty and may contain no more than five Wikipedia
editions. The source edition can be outside `projects`: it is used to resolve
the confirmed canonical article, not necessarily to compare its views. Dates
are inclusive and cannot extend into the future.

## Topic baskets

For a broader topic, replace the single-article fields with `topic.articles`:

```yaml
topic:
  articles:
    - source_project: en.wikipedia
      source_title: English language
      qid: Q1860
      role: primary
      label: Learning English
    - source_project: en.wikipedia
      source_title: Second-language acquisition
      qid: Q8162
      role: supporting
      weight: 0.5
```

Every article must have a user-confirmed QID. A basket must contain exactly
one `primary` article; other articles are `supporting`. Weights are preserved
in the configuration for future use, but the current implementation produces
separate reports and does not aggregate the basket by default.
