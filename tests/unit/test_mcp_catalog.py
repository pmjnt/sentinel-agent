from mcp.types import Tool, ToolAnnotations

from app.mcp.binance import to_catalog_entries


def test_catalog_conversion_preserves_only_review_metadata() -> None:
    tool = Tool.model_validate(
        {
            "name": "sample_market_reader",
            "title": "Sample reader",
            "description": "Read sample market data.",
            "inputSchema": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
            },
            "outputSchema": {
                "type": "object",
                "properties": {"price": {"type": "number"}},
            },
            "annotations": {
                "readOnlyHint": True,
                "destructiveHint": False,
            },
            "icons": [{"src": "https://example.invalid/icon.png"}],
            "_meta": {"secret-provider-field": "must-not-leak"},
        }
    )

    entry = to_catalog_entries([tool])[0]

    assert entry.model_dump() == {
        "name": "sample_market_reader",
        "title": "Sample reader",
        "description": "Read sample market data.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
        },
        "output_schema": {
            "type": "object",
            "properties": {"price": {"type": "number"}},
        },
        "read_only_hint": True,
        "destructive_hint": False,
    }


def test_missing_annotations_remain_unknown() -> None:
    tool = Tool(
        name="unclassified_tool",
        description="No trusted classification is available.",
        inputSchema={"type": "object"},
    )

    entry = to_catalog_entries([tool])[0]

    assert entry.read_only_hint is None
    assert entry.destructive_hint is None


def test_catalog_keeps_server_order() -> None:
    tools = [
        Tool(name="second", inputSchema={"type": "object"}),
        Tool(
            name="first",
            inputSchema={"type": "object"},
            annotations=ToolAnnotations(readOnlyHint=True),
        ),
    ]

    assert [entry.name for entry in to_catalog_entries(tools)] == [
        "second",
        "first",
    ]
