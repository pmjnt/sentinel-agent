# Natural Analysis Responses

## Goal

Let Sentinel answer like a natural conversational assistant instead of always
using the same Assessment, Rationale, Recommendation, and Limitations headings.

## Design

- Remove the mandatory four-heading instruction from the active Agent prompt.
- Let the LLM choose paragraphs, short headings, bullets, or numbered choices
  based on the content and response length.
- Keep responses concise and use the user's language.
- Every personalized conclusion or suggestion must remain grounded in the current
  `PortfolioAnalysis` returned by tools.
- Important uncertainty or missing information must still be disclosed, but it
  does not need a dedicated `Limitations` heading.
- Keep authoritative `Verified tool facts` rendered separately by deterministic
  UI code.

## Testing

- Assert the prompt no longer requires the four fixed headings.
- Assert it explicitly permits a natural response structure.
- Run prompt tests, the full Python suite, and UI tests.
