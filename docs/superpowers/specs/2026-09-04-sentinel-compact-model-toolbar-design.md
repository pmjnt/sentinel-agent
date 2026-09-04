# Sentinel Compact Model Toolbar Design

## Goal

Reduce the space used by provider and model configuration without making the controls too small.

## Approved layout

Replace the current two-field block, route preview, and explanatory paragraph with one compact horizontal toolbar:

```text
Provider  [Gemini]    Model  [gemini-3.5-flash-lite]    FREE TIER
```

- Keep labels beside their controls instead of above them.
- Keep controls at least 44px high for accessible interaction.
- Limit provider width and give the model only the width needed for its identifier.
- Remove the LiteLLM route preview and long free-tier explanation from the form. The full calling flow remains documented in `README.md`.
- Preserve the existing provider/model behavior and Gemini default.
- On narrow screens, wrap cleanly into rows without horizontal scrolling.

## Scope

This is a markup and CSS layout change only. It does not connect the static UI to the Python Agent or change model-routing behavior.

## Verification

- Existing JavaScript and Python tests remain green.
- Static checks confirm the compact toolbar markup and removal of the old route-preview block.
- Review the toolbar at desktop and mobile widths when a browser session is available.
