#!/usr/bin/env python3
"""从已核验 Ledger 生成 article、conference 或 preprint BibTeX。

Render article, conference, or preprint BibTeX from verified Ledger citations.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
from common.canonical_json import load_json


def escape(value) -> str:
    text = str(value)
    return re.sub(r"(?<!\\)([&%_$#])", r"\\\1", text)


def render(ledger) -> str:
    entries = []
    for citation in ledger.get("citations", []):
        if citation.get("verified") is not True:
            raise ValueError(f"citation {citation.get('citation_id')} is not verified")
        kind = citation.get("entry_type", "article")
        bib_kind = {"article": "article", "conference": "inproceedings", "preprint": "misc"}.get(kind)
        if not bib_kind:
            raise ValueError(f"unsupported citation entry_type: {kind}")
        required = ("citation_id", "title", "authors", "year")
        if any(not citation.get(field) for field in required):
            raise ValueError(f"citation is missing required fields: {citation.get('citation_id')}")
        fields = [("title", citation["title"]), ("author", citation["authors"]), ("year", citation["year"])]
        if kind == "article":
            fields.extend((key, citation[key]) for key in ("journal", "doi") if citation.get(key))
        elif kind == "conference":
            if not citation.get("booktitle"): raise ValueError("conference citation requires booktitle")
            fields.extend((("booktitle", citation["booktitle"]), *( (key, citation[key]) for key in ("doi", "pages") if citation.get(key))))
        else:
            if not citation.get("eprint"): raise ValueError("preprint citation requires eprint")
            fields.extend((("eprint", citation["eprint"]), ("archivePrefix", citation.get("archive_prefix", "arXiv"))))
        body = ",\n".join(f"  {key}={{{escape(value)}}}" for key, value in fields)
        entries.append(f"@{bib_kind}{{{citation['citation_id']},\n{body}\n}}")
    return "\n\n".join(entries) + ("\n" if entries else "")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("ledger"); parser.add_argument("--output", required=True); args = parser.parse_args()
    Path(args.output).write_text(render(load_json(args.ledger)), encoding="utf-8")


if __name__ == "__main__": main()
