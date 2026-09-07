# Inline Numbered List Rendering

## Goal

Make model responses such as `1. ETH ... 2. BTC ... 3. SOL ...` readable by
rendering each numbered choice on its own line in the chat UI.

## Design

- Extend the existing safe Markdown parser in `web/app.js`; do not use raw HTML.
- Recognize an ordered list only when a text segment contains a sequence beginning
  with `1.` followed by at least `2.`.
- Support both inline and already line-separated numbered items.
- Return an `ordered-list` block containing plain item strings.
- Render that block as an `<ol>` with one `<li>` per option, reusing the existing
  safe inline-bold renderer.
- Do not interpret decimal values such as `1.5%` as list markers because a marker
  must be followed by whitespace and form a numbered sequence.

## Testing

- Add a parser test for the reported inline `1. ... 2. ... 3. ...` response.
- Add a regression test proving decimal text remains a paragraph.
- Run the complete Node UI test suite and existing Python suite.
