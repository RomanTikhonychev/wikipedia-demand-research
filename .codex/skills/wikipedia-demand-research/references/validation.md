# Validation record

Use this record to distinguish checks that have passed from checks that remain
to be performed. A passing unit-test suite is evidence for the code paths it
covers, not proof that every agent will follow the skill instructions.

## Completed local checks

| Area | Evidence |
| --- | --- |
| Skill structure | `quick_validate.py` accepts the skill directory. |
| Data calculations | The unit suite covers URL encoding, daily gaps versus zeros, complete-month rules, reliability, research specifications, unique output folders, and copying the applied specification. |
| Reproducibility | A test verifies that an existing cached response can be read in `--offline` mode. |
| Deliverables | The PDF test verifies a PDF header, a single page, and the quality table; the Markdown report test checks that coverage and limits are present. |
| Manual report review | A generated one-page PDF was rendered and visually inspected for clipped content. |

Run the two local checks from the repository root:

```bash
.venv/bin/python -m unittest discover -s .codex/skills/wikipedia-demand-research/tests -v
.venv/bin/python /Users/roman/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/skills/wikipedia-demand-research
```

## Required low-cost-model scenario

Status: **pending external model availability**. The OpenRouter profile is
prepared, but a free-model quota prevented the full scenario from being run.
Do not describe this requirement as passed until this scenario is completed.

In a new Codex chat running a tool-capable low-cost model, submit:

```text
Використай $wikipedia-demand-research. Досліди інтерес до Tesla в українській та англійській Вікіпедіях за 2024 рік.
```

Record the actual OpenRouter model selected, date, prompt, final answer, and
the path to the output. The run passes only if the agent first presents
candidate articles and requests confirmation; after confirmation it must create
or reuse a reproducible `research.yaml`, write a distinct output directory,
and base its conclusion on the manifest and CSV rather than the chart alone.

## Release decision

The skill is ready for normal local use when the local checks pass. It is ready
to claim compliance with the inexpensive-model requirement only after the
low-cost-model scenario passes and its evidence is recorded here.
