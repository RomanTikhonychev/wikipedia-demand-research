# Wikipedia Demand Research

A self-contained Codex skill for reproducible first-pass research into
Wikipedia article pageviews across language editions. It creates a chart, a
one-page PDF report, a Markdown report, a monthly CSV, and a manifest of the
data requests used.

It measures interest in named Wikipedia article proxies. It does **not**
measure market size, willingness to pay, unique people, or country-level
demand.

Each report separates the observed pageview trend, calculated confidence in
that observation, and the user-confirmed relevance of the selected article to
the decision being considered. If no decision context is supplied, relevance
is reported as `not assessed`.

## Install in a repository

Copy this directory into the target repository at:

```text
.codex/skills/wikipedia-demand-research/
```

From the repository root, prepare an isolated Python environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r .codex/skills/wikipedia-demand-research/requirements.txt
```

The dependencies are pinned in both `requirements.txt` and `pyproject.toml`.

## Use in Codex

In a Codex chat, ask for the skill explicitly:

```text
Використай $wikipedia-demand-research. Порівняй інтерес до інтервального
голодування в польській та чеській Wikipedia за 2024 рік.
```

If the request does not name an exact Wikipedia article, the agent should show
up to four search candidates at once and wait for confirmation. It should not
silently choose an article or begin collecting data before that confirmation.

By default, reports use Wikimedia's `user` traffic across all access types;
traffic categorized as `spider` or `automated` is excluded. To study one device
access type, add `--access desktop`, `--access mobile-web`, or
`--access mobile-app` when creating a research specification or direct run.

## Run the included example

The example is a confirmed single-article study. Copy it to a local working
directory before editing it; that keeps the packaged example unchanged.

```bash
mkdir -p researches/english-language-de-uk
cp .codex/skills/wikipedia-demand-research/examples/research.yaml \
  researches/english-language-de-uk/research.yaml
.venv/bin/python .codex/skills/wikipedia-demand-research/scripts/compare_topic.py \
  --research researches/english-language-de-uk/research.yaml \
  --user-agent "my-research-skill/0.1 (contact@example.com)"
```

Replace the example contact with a real email address or URL, or set
`WIKIMEDIA_USER_AGENT` once in your environment. Each run creates a new
timestamped directory under `researches/english-language-de-uk/runs/`.

For a new study, use `--init-research` after confirming the article. The
[saved-research guide](references/research-spec.md) describes the format,
topic baskets, and revision rules.

## Inspect the model-comparison runs

Committed example runs used to check the full workflow on different models are
in [evaluation/model-comparison-runs/](evaluation/model-comparison-runs/).
Each run preserves its applied `research.yaml`, raw Wikimedia response,
monthly CSV, chart, PDF and Markdown report, and manifest. They are examples
for inspection and reproducibility, not a source of fresh research results.

## Verify the package

Run these commands from the repository root after installation:

```bash
.venv/bin/python -m unittest discover -s .codex/skills/wikipedia-demand-research/tests -v
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  .codex/skills/wikipedia-demand-research
```

The second command is available in Codex installations that include the
`skill-creator` system skill. The validation protocol, including the remaining
inexpensive-model scenario, is in [references/validation.md](references/validation.md).

## Repository hygiene

Keep generated reports, raw API data, caches, and your working
`research.yaml` files outside this skill directory. In this repository,
`outputs/` and `researches/` are already ignored by Git. Commit the skill code,
tests, fixtures, references, and this README; do not commit personal research
runs or API keys.
