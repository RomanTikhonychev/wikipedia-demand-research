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

## Repository layout

```text
.codex/skills/wikipedia-demand-research/  # skill code, tests, docs, example
outputs/                                  # local generated reports; ignored
researches/                               # local study specifications; ignored
```

Generated reports, caches, local research specifications, virtual
environments, and API keys must not be committed.
