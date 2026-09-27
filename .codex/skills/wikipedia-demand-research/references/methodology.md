# Methodology and limits

## Research contract

This skill creates reproducible, first-pass evidence about interest in a
Wikipedia topic. It supports a decision to investigate a topic or language
audience further, to note a stable or changing information-interest signal, or
to conclude that the available data are insufficient. It is not a market
research instrument on its own.

Use language that keeps the claim tied to the data, such as:

- “There is a signal for further validation.”
- “Interest in the related Wikipedia topic increased over the selected period.”
- “The data are insufficient for a reliable conclusion.”

Do not turn these signals into claims about market size, product demand,
willingness to pay, unique people, a country's population, or the size of a
country's market. A Wikipedia language edition can be read well beyond the
country or countries commonly associated with that language.

## What the script measures

The comparison script resolves the source article's Wikidata item, uses its
language links to identify corresponding articles, requests daily pageviews for
each article with Wikimedia's `all-access` and `user` filters, then sums the
returned days into calendar months. "User" is intended to exclude traffic that
Wikimedia classifies as spider or automated traffic; it is not a count of unique
people. For complete calendar months, it also divides article views by the
monthly views for the relevant Wikipedia edition.

The caller must identify itself to Wikimedia with a `User-Agent` containing a
real contact URL or email. This is an API access requirement, not analysis data.

## Decisions this can support

The output can support a narrowly phrased claim such as: “Views of the linked
article rose or fell over the selected period.” It can motivate a product
research hypothesis or help prioritize a language audience for further
research. `share_of_project_views` makes comparisons between different-sized
language editions more meaningful, but does not make them a measure of a
market.

## What it does not measure

Do not treat article views as the size of a market, demand for a product,
willingness to pay, unique users, or the population of a country. A language
edition may be read outside the country associated with that language.

## Checks before reporting a trend

1. Verify that the requested article is the intended concept.
2. Inspect the full date range and flag any month with fewer than its normal
   number of daily records.
3. Compare a month with the same month in the prior year when seasonality may
   matter.
4. Note a single unusual spike rather than allowing it to stand in for a trend.

## Trend and reliability rules in version 0.1

For six or more complete months, `period_change` compares the average of the
first three complete months with the average of the last three. At 24 complete
months, `year_over_year` compares the latest 12 months with the preceding 12.
These are descriptive indicators, not forecasts or tests of statistical
significance.

Reliability starts as medium for 6-23 complete months and high for 24 or more.
It is reduced for very low typical traffic or when one month exceeds three times
the median. The exact reasons appear in the report and manifest.
