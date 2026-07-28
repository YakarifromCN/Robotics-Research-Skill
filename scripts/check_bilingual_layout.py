#!/usr/bin/env python3
"""检查 skill 说明是否遵循“完整中文在前、完整英文在后”的布局。

Check whether skill documentation follows the complete-Chinese-first,
complete-English-second layout.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


ENGLISH_MARKER = re.compile(r"^#\s*(?:English Version|English)", re.MULTILINE)
CJK = re.compile(r"[\u3400-\u9fff]")
LATIN_WORD = re.compile(r"[A-Za-z]{3,}")


def markdown_findings(path: Path) -> list[dict[str, str]]:
    """检查一个 Markdown 文件的双语分区顺序与非空内容。

    Check bilingual section order and non-empty content in one Markdown file.
    """

    text = path.read_text(encoding="utf-8")
    en = ENGLISH_MARKER.search(text)
    findings: list[dict[str, str]] = []
    if en is None:
        findings.append({"code": "EN_SECTION_MISSING", "path": str(path)})
    if en is None:
        return findings
    zh_body = text[:en.start()]
    en_body = text[en.end() :]
    if not CJK.search(zh_body):
        findings.append({"code": "ZH_BODY_EMPTY", "path": str(path)})
    if not LATIN_WORD.search(en_body):
        findings.append({"code": "EN_BODY_EMPTY", "path": str(path)})
    return findings


def python_findings(path: Path) -> list[dict[str, str]]:
    """检查 Python 模块 docstring 是否中文在英文之前。

    Check that a Python module docstring places Chinese before English.
    """

    source = path.read_text(encoding="utf-8-sig")
    try:
        module = ast.parse(source)
    except SyntaxError as exc:
        return [{"code": "PYTHON_SYNTAX", "path": str(path), "message": str(exc)}]
    doc = ast.get_docstring(module, clean=False)
    if not doc:
        return [{"code": "MODULE_DOCSTRING_MISSING", "path": str(path)}]
    zh = CJK.search(doc)
    en = LATIN_WORD.search(doc)
    findings: list[dict[str, str]] = []
    if zh is None:
        findings.append({"code": "DOCSTRING_ZH_MISSING", "path": str(path)})
    if en is None:
        findings.append({"code": "DOCSTRING_EN_MISSING", "path": str(path)})
    if zh is not None and en is not None and zh.start() > en.start():
        findings.append({"code": "DOCSTRING_LANGUAGE_ORDER", "path": str(path)})
    return findings


def main() -> int:
    """运行项目级双语布局审计并输出 JSON。

    Run the project-level bilingual-layout audit and emit JSON.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    docs = sorted(root.glob("skills/*/SKILL.md")) + sorted(root.glob("skills/*/references/*.md")) + sorted(root.glob("skills/*/agents/*.md"))
    scripts = sorted(root.glob("skills/*/scripts/*.py"))
    findings: list[dict[str, str]] = []
    for path in docs:
        findings.extend(markdown_findings(path))
    for path in scripts:
        findings.extend(python_findings(path))
    output = {
        "tool": "check_bilingual_layout.py",
        "status": "fail" if findings else "pass",
        "checked": {"markdown": len(docs), "python": len(scripts)},
        "findings": findings,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
