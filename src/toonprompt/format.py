from __future__ import annotations

FORMAT_VERSION = "1"

FORMAT_RULES = {
    "1": {
        "indent": 2,
        "array_header": "name[count]:",
        "table_header": "name[count]{field1,field2}:",
        "escapes": ["comma", "newline", "backslash"],
        "fail_strategy": "pass-through",
    }
}


def supported_format(version: str) -> bool:
    return version in FORMAT_RULES
