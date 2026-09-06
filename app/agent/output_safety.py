import re

from agents import ModelBehaviorError


_POSITIVE_EXECUTION_LANGUAGE = re.compile(
    r"\border\s+(?:was\s+)?(?:placed|filled|completed|executed)\b"
    r"|\bexecution\s+(?:was\s+)?(?:completed|successful|succeeded)\b"
    r"|\b(?:i|we|sentinel)\s+(?:have\s+)?executed\b"
    r"|\b(?:trade|sale|purchase)\s+(?:was\s+)?"
    r"(?:completed|executed|filled)\b"
    r"|(?:giao dịch|lệnh|lệnh bán|lệnh mua).{0,30}"
    r"(?:đã\s+)?(?:được\s+)?(?:thực hiện|đặt|khớp|hoàn (?:tất|thành))",
    flags=re.IGNORECASE | re.DOTALL,
)

_NEGATED_EXECUTION_PREFIX = re.compile(
    r"(?:\bno\b|\bnot\b|\bnever\b|không|chưa)(?:\s+\S+){0,4}\s*$",
    flags=re.IGNORECASE,
)

_UNVERIFIED_RESERVED_LANGUAGE = re.compile(
    r"\bblocked\b"
    r"|\brequires?[\s_-]+approval\b"
    r"|\bsafe(?:[\s_-]+to)?[\s_-]+propose\b"
    r"|\border\s+(?:was\s+)?(?:placed|filled|completed|executed)\b"
    r"|\bexecution\s+(?:was\s+)?(?:completed|successful|succeeded)\b"
    r"|\b(?:i|we|sentinel)\s+(?:have\s+)?executed\b"
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
    if _contains_positive_execution_claim(normalized):
        raise ModelBehaviorError(
            "Agent used reserved risk or execution language."
        )
    return normalized


def _contains_positive_execution_claim(output: str) -> bool:
    for match in _POSITIVE_EXECUTION_LANGUAGE.finditer(output):
        prefix = output[max(0, match.start() - 40):match.start()]
        if _NEGATED_EXECUTION_PREFIX.search(prefix):
            continue
        return True
    return False


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
