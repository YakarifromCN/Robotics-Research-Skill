#!/usr/bin/env python3
"""审计 LaTeX 主张、句子映射与冻结数字。

Audit LaTeX claims, sentence mappings, and frozen numbers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
from common.canonical_json import load_json

TERMS = ["robust", "real-time", "safe", "lightweight", "significant", "generaliz", "universal", "first", "comprehensive", "鲁棒", "实时", "安全", "轻量", "显著", "泛化", "普适", "首次", "全面", "任意环境"]
COMMAND_NUMBER = re.compile(r"\\num\{([^}]+)\}|\\SI\{([^}]+)\}\{([^}]+)\}")
BARE_NUMBER = re.compile(r"(?<![A-Za-z\\{}])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
CLAIM_REF = re.compile(r"\\claimref\{([^}]+)\}")
RESULT_REF = re.compile(r"\\resultref\{([^}]+)\}")
NUMBER_REF = re.compile(r"\\numref\{([^}]+)\}")
CITATION_REF = re.compile(r"\\cite(?:[a-zA-Z]*)?\{([^}]+)\}")
SUPPORT_LANGUAGE = re.compile(r"\b(supports?|supported|demonstrates?|effective|improves?|outperforms?|proves?)\b|支持|证明|有效|提升|优于", re.I)
UNDERCLAIM_CUE = re.compile(
    r"\b(?:preliminary|promising|tentatively|may\s+(?:tentatively\s+)?suggest|might\s+suggest|could\s+possibly|appears?\s+to)\b|"
    r"初步(?:结果|证据)?|可能(?:初步)?表明|有望",
    re.I,
)
WORK_LOG_CUE = re.compile(
    r"\b(?:we\s+(?:first|initially)|then\s+tried|after\s+several\s+attempts|eventually\s+(?:found|discovered))\b|"
    r"我们先|经过多次尝试|后来尝试|最终发现",
    re.I,
)


def _canonical_number(value) -> str | None:
    try:
        return str(Decimal(str(value)).normalize())
    except (InvalidOperation, ValueError):
        return None


def audit(text, ledger):
    stripped = re.sub(r"%.*", "", text); findings = []
    for term in TERMS:
        if re.search(re.escape(term), stripped, re.I): findings.append({"level": "warn", "code": "CLAIM_SCOPE_TERM", "term": term})
    if "{{N" in stripped: findings.append({"level": "fail", "code": "UNRENDERED_NUMBER"})
    known = {_canonical_number(n.get("value")) for n in ledger.get("numbers", [])}
    known.discard(None)
    command_spans = []
    for match in COMMAND_NUMBER.finditer(stripped):
        command_spans.append(match.span())
        value = match.group(1) or match.group(2)
        if _canonical_number(value) not in known:
            findings.append({"level": "fail", "code": "UNTRACKED_LATEX_NUMBER", "value": value})
    without_commands = list(stripped)
    for start, end in command_spans:
        without_commands[start:end] = " " * (end - start)
    for token in BARE_NUMBER.findall("".join(without_commands)):
        if not re.fullmatch(r"(?:19|20)\d{2}", token) and _canonical_number(token) not in known:
            findings.append({"level": "warn", "code": "UNTRACKED_NUMBER", "value": token})
    claims = {row.get("claim_id") for row in ledger.get("claims", []) if isinstance(row, dict)}
    claim_states = {row.get("claim_id"): row.get("evidence_state") for row in ledger.get("claims", []) if isinstance(row, dict)}
    result_ids = {item for row in ledger.get("claims", []) if isinstance(row, dict) for field in ("support_result_ids", "boundary_result_ids") for item in row.get(field, [])}
    result_ids |= {row.get("external_evidence_id") for row in ledger.get("external_evidence_registry", []) if isinstance(row, dict)}
    number_ids = {row.get("number_id") for row in ledger.get("numbers", []) if isinstance(row, dict)}
    citation_ids = {row.get("citation_id") for row in ledger.get("citations", []) if isinstance(row, dict)}
    for rid in RESULT_REF.findall(stripped):
        if rid not in result_ids: findings.append({"level": "fail", "code": "UNKNOWN_RESULT_REF", "result_id": rid})
    for nid in NUMBER_REF.findall(stripped):
        if nid not in number_ids: findings.append({"level": "fail", "code": "UNKNOWN_NUMBER_REF", "number_id": nid})
    for group in CITATION_REF.findall(stripped):
        for citation_id in (item.strip() for item in group.split(",")):
            if citation_id not in citation_ids: findings.append({"level": "fail", "code": "UNKNOWN_CITATION_REF", "citation_id": citation_id})
    sentence_refs = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", stripped):
        if UNDERCLAIM_CUE.search(sentence):
            findings.append({"level": "warn", "code": "UNDERCLAIM_CANDIDATE", "sentence": sentence.strip(), "rule": "contextual review required; strengthening is allowed only up to the frozen ledger ceiling"})
        if WORK_LOG_CUE.search(sentence):
            findings.append({"level": "warn", "code": "WORK_LOG_CANDIDATE", "sentence": sentence.strip(), "rule": "retain only when the sequence is evidence or mechanism"})
        refs = CLAIM_REF.findall(sentence)
        for cid in refs:
            if cid not in claims: findings.append({"level": "fail", "code": "UNKNOWN_CLAIM_REF", "claim_id": cid})
            elif claim_states.get(cid) in {"INCONCLUSIVE", "NOT_SUPPORTED"} and SUPPORT_LANGUAGE.search(sentence):
                findings.append({"level": "fail", "code": "CLAIM_STATUS_MISMATCH", "claim_id": cid, "state": claim_states[cid]})
        if refs: sentence_refs.append({"claim_ids": refs, "sentence": sentence.strip()})
    return findings, sentence_refs


def claim_trace(ledger, sentence_refs=None):
    claims = {row.get("claim_id"): row for row in ledger.get("claims", []) if isinstance(row, dict) and row.get("claim_id")}
    trace = {cid: {"evidence_state": row.get("evidence_state"), "support_result_ids": row.get("support_result_ids", []), "boundary_result_ids": row.get("boundary_result_ids", []), "number_ids": [], "figure_ids": [], "sentences": []} for cid, row in claims.items()}
    for number in ledger.get("numbers", []):
        for cid in number.get("claim_ids", []):
            if cid in trace: trace[cid]["number_ids"].append(number.get("number_id"))
    for figure in ledger.get("figures", []):
        for cid in figure.get("claim_ids", []):
            if cid in trace: trace[cid]["figure_ids"].append(figure.get("figure_id"))
    for row in sentence_refs or []:
        for cid in row["claim_ids"]:
            if cid in trace: trace[cid]["sentences"].append(row["sentence"])
    return trace


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("manuscript"); parser.add_argument("ledger"); args = parser.parse_args()
    ledger = load_json(args.ledger); findings, sentences = audit(Path(args.manuscript).read_text(encoding="utf-8"), ledger)
    print(json.dumps({"valid": not any(x["level"] == "fail" for x in findings), "findings": findings, "claim_trace": claim_trace(ledger, sentences)}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if any(x["level"] == "fail" for x in findings) else 0)


if __name__ == "__main__": main()
