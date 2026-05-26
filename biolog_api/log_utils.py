import re

_PATTERNS = [
    (re.compile(r'("user_id"\s*:\s*)"[^"]*"'), r'\1"****"'),
    (re.compile(r'("request_id"\s*:\s*)"[^"]*"'), r'\1"****"'),
    (re.compile(r"(user_id=)[^\s,}]+"), r"\1****"),
    (re.compile(r"(request_id=)[^\s,}]+"), r"\1****"),

    (re.compile(
        r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b",
        re.IGNORECASE,
    ), "****"),

    (re.compile(r"\b[a-f0-9]{32}\b", re.IGNORECASE), "****"),

    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "***@***"),
]


def mask_pii(text: str) -> str:
    if text is None:
        return ""
    text = str(text)
    for p, r in _PATTERNS:
        text = p.sub(r, text)
    return text
