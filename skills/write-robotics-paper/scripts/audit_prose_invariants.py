#!/usr/bin/env python3
"""检查语言修订的可机械核对项；语义仍需人工核对。

Check mechanical prose invariants; semantic review remains required.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re


def audit(before, after, protected=()):
    patterns = {
        "numbers": r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?",
        "citations": r"\\(?:cite\w*|ref|eqref|label)\*?(?:\[[^]]*\])?\{[^}]+\}",
        "inline_math": r"\$[^$\n]+\$|\\\([^\n]*?\\\)",
        "evidence_states": r"\b(?:SUPPORTED|NOT_SUPPORTED|INCONCLUSIVE|PARTIALLY_SUPPORTED|EVIDENCE_GAPS)\b",
    }
    changed = [name for name, pattern in patterns.items() if Counter(re.findall(pattern, before)) != Counter(re.findall(pattern, after))]
    lost = [value for value in protected if value in before and value not in after]
    return {"mechanical_invariants_match": not changed and not lost, "changed_categories": changed,
            "missing_protected_tokens": lost, "semantic_review_required": True, "handoff_ready": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.before.read_text(), args.after.read_text()), ensure_ascii=False))
