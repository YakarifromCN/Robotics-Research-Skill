#!/usr/bin/env python3
"""评审输出语言策略。 / Output-language policy for review runs."""

from __future__ import annotations

import re


def normalize_language(value: object) -> str:
    """接受任意单语，或 ``en+任意语言`` 双语规格。

    Accept any non-empty single-language label, or an ``en+<any-language>``
    bilingual specification.  The value is a label, not a fixed enum.
    """

    if not isinstance(value, str):
        raise ValueError("TARGET_LANGUAGE_REQUIRED: provide --language <language> or --language en+<language>")
    language = value.strip()
    if not language or re.search(r"[\r\n\x00]", language):
        raise ValueError("TARGET_LANGUAGE_REQUIRED: language must be a non-empty single line")
    if "+" in language:
        left, right = language.split("+", 1)
        if left.strip().lower() != "en" or not right.strip() or "+" in right:
            raise ValueError("LANGUAGE_FORMAT_INVALID: bilingual output must use en+<any-language>")
    return language


def language_mode(language: str) -> str:
    return "bilingual" if "+" in language else "single"
