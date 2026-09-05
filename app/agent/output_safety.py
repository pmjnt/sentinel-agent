import re

from agents import ModelBehaviorError


_RESERVED_FINANCIAL_LANGUAGE = re.compile(
    r"\bblocked\b"
    r"|\brequires?[\s_-]+approval\b"
    r"|\bsafe(?:[\s_-]+to)?[\s_-]+propose\b"
    r"|\bexecut(?:e|ed|ing|ion)\b"
    r"|\border\s+(?:was\s+)?(?:placed|filled|completed)\b"
    r"|\b(?:trade|sale|purchase)\s+(?:was\s+)?"
    r"(?:completed|executed|filled)\b"
    r"|(?:giao dịch|lệnh|lệnh bán|lệnh mua).{0,30}"
    r"(?:đã\s+)?(?:được\s+)?(?:thực hiện|đặt|khớp|hoàn (?:tất|thành))"
    r"|(?:cần|yêu cầu).{0,20}phê duyệt"
    r"|an toàn.{0,20}đề xuất",
    flags=re.IGNORECASE | re.DOTALL,
)

_UNVERIFIED_RESERVED_LANGUAGE = re.compile(
    r"\bblocked\b"
    r"|\brequires?[\s_-]+approval\b"
    r"|\bsafe(?:[\s_-]+to)?[\s_-]+propose\b"
    r"|\border\s+(?:was\s+)?(?:placed|filled|completed|executed)\b"
    r"|\b(?:trade|sale|purchase)\s+(?:was\s+)?"
    r"(?:completed|executed|filled)\b"
    r"|(?:giao dịch|lệnh|lệnh bán|lệnh mua).{0,30}"
    r"(?:đã\s+)?(?:được\s+)?(?:thực hiện|đặt|khớp|hoàn (?:tất|thành))"
    r"|(?:cần|yêu cầu).{0,20}phê duyệt"
    r"|an toàn.{0,20}đề xuất",
    flags=re.IGNORECASE | re.DOTALL,
)


def validate_qualitative_output(output: str) -> str:
    normalized = output.strip()
    if not normalized:
        raise ModelBehaviorError("Agent returned empty text output.")
    if _RESERVED_FINANCIAL_LANGUAGE.search(normalized):
        raise ModelBehaviorError(
            "Agent used reserved risk or execution language."
        )
    return normalized


def validate_non_analysis_output(output: str) -> str:
    """Reject authoritative claims when no deterministic analysis exists."""
    normalized = output.strip()
    if not normalized:
        raise ModelBehaviorError("Agent returned empty text output.")
    if _UNVERIFIED_RESERVED_LANGUAGE.search(normalized):
        raise ModelBehaviorError(
            "Agent used reserved risk or execution language."
        )
    return normalized
