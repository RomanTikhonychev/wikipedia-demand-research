# Roadmap

The current skill is intentionally narrow: it compares confirmed Wikipedia
article proxies, preserves raw inputs, and produces separate reports for a
topic basket. Extend it only when a real research question requires the extra
complexity.

1. **Finish the low-cost-model evaluation.** Record one complete OpenRouter or
   equivalent run using the protocol in [validation.md](validation.md).
2. **Add language and report localization.** Localize the report narrative and
   right-to-left layout only after choosing the intended reader languages.
3. **Improve operational robustness.** Add configurable cache freshness,
   clearer recovery guidance for rate limits, and integration tests with saved
   API fixtures.
4. **Add optional basket aggregation.** Define a transparent normalization and
   weighting method, show the per-article components, and require explicit
   user approval before aggregating.
5. **Add decision criteria only on request.** Let a user supply their own
   criteria for a follow-up decision; do not convert pageviews into market
   demand or a build recommendation.
6. **Package for broader reuse.** Add a concise usage guide and a clean-room
   installation check once the workflow and its dependencies stabilize.
