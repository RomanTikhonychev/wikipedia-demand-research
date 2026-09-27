# Wikipedia Demand Research

This repository contains a Codex skill for reproducible first-pass research
into Wikipedia article pageviews across language editions. It produces a chart,
a one-page PDF report, a Markdown report, a monthly CSV, and a manifest of the
data used.

The skill measures interest in confirmed Wikipedia article proxies. It does
not measure market size, willingness to pay, unique people, or country-level
demand.

## Skill

The installable skill is at
[`.codex/skills/wikipedia-demand-research`](.codex/skills/wikipedia-demand-research/).
Its complete setup, usage, testing, and repository-hygiene instructions are in
the [skill README](.codex/skills/wikipedia-demand-research/README.md).

To invoke it in Codex, use:

```text
Використай $wikipedia-demand-research. Порівняй інтерес до інтервального
голодування в польській та чеській Wikipedia за 2024 рік.
```

## Test runs

The reproducible artifacts from a model-comparison exercise are committed in
[`model-comparison-runs/`](model-comparison-runs/). The task given to each
model was:

> Ми думаємо додати курс з астрономії до освітнього застосунку. Чи зростає
> інтерес до цієї теми в україномовній Wikipedia, і наскільки цьому зростанню
> можна довіряти?

The intended scope was the Ukrainian Wikipedia article **«Астрономія»** over
the latest 24 months. Each run keeps its applied `research.yaml`, manifest,
raw API response, monthly CSV, chart, and reports, so its result can be
inspected or reproduced.

| Run | Period actually analysed | Reported result |
| --- | --- | --- |
| `openrouter:free low` | 2024-09-01 to 2026-08-31 (24 complete months) | Declining: −88%; medium reliability because a monthly spike exceeds three times the median. |
| `gpt-5.6 Terra High` | 2024-09-01 to 2026-08-31 (24 complete months) | Declining: −88%; medium reliability because a monthly spike exceeds three times the median. |

Thus, neither test reports growth in views of the selected article. Both runs
use the same requested 24-month window and report the same descriptive result.
These results are first-pass Wikipedia pageview signals only: they do not
establish product demand, market size, unique users, or willingness to pay.
Both reports leave decision relevance unassessed, so the suitability of this
one article as a proxy for an astronomy course still needs confirmation.

## Repository layout

```text
.codex/skills/wikipedia-demand-research/  # skill code, tests, docs, example
model-comparison-runs/                    # committed model-comparison artifacts
outputs/                                  # local generated reports; ignored
researches/                               # local study specifications; ignored
```

Other generated reports, caches, local research specifications, virtual
environments, and API keys must not be committed. The committed test artifacts
above are the deliberate exception.
