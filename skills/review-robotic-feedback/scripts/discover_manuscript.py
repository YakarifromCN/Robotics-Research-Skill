#!/usr/bin/env python3
"""发现并冻结机器人稿件图、工件依赖与评审范围。

Discover and freeze the manuscript graph, artifact dependencies, and review scope.

The output is deliberately a *snapshot*: downstream reviewers must not silently
read a file that changed after discovery.  Missing scientific contracts are
represented explicitly instead of being encoded as ambiguous ``null`` values.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
import sys

sys.path.insert(0, str(ROOT))

try:
    from common.canonical_json import JsonIntegrityError, load_json, sha256_file, write_json
except ModuleNotFoundError:  # 独立安装兼容 / standalone installed Skill
    from review_runtime import JsonIntegrityError, load_json, sha256_file, write_json
from review_language import language_mode, normalize_language


IGNORE_DIRS = {
    ".git",
    "build",
    "output",
    "_minted-",
    "reviews",
    "review",
    "old",
    "archive",
    "previous",
    "submitted",
}
EXCLUDED_NAMES = re.compile(r"^(response|letter|review|old|draft|slides|presentation)", re.I)
FIG_EXT = {".pdf", ".png", ".eps", ".jpg", ".jpeg", ".svg", ".webp"}
REVIEWERS = (
    "manuscript-proofreading",
    "robotics-contribution-review",
    "control-optimization-review",
    "robot-learning-review",
    "hardware-review",
    "evidence-artifact-audit",
    "venue-compliance-review",
)

# These are routing hints, not scientific verdicts.  They activate a reference
# pack only when the manuscript/contracts contain an observable signal.
PACK_RULES = {
    "learning": re.compile(
        r"\b(learn(?:ing|ed)?|policy|reinforcement|imitation|demonstration|checkpoint|dataset|training|\bseed\b)\b",
        re.I,
    ),
    "control-optimization": re.compile(
        r"\b(controller|control|feedback|stability|stable|robust|optimization|optimizer|dynamics|kinematic|trajectory|real[- ]?time|solver|gain)\b",
        re.I,
    ),
    "hardware": re.compile(
        r"\b(robot|hardware|sensor|actuator|firmware|calibration|calibrat|motor|force[- ]?torque|emergency stop|e[- ]?stop|workspace|payload|communication|ros|real[- ]robot)\b",
        re.I,
    ),
    "evidence-artifact": re.compile(
        r"\b(result bundle|claim ledger|trial|experiment|metric|ablation|artifact|reproduc|log|success rate|failure|statistic|participant|session)\b",
        re.I,
    ),
    "soft-body": re.compile(r"\b(soft robot|soft[- ]body|compliant|elastomer|continuum|deformable|柔性|软体)\b", re.I),
    "human-interaction": re.compile(r"\b(human|user|participant|hri|human[- ]robot|shared control|人体|人机)\b", re.I),
    "industrial": re.compile(r"\b(industrial|factory|manufactur|assembly|inspection|warehouse|工厂|工业)\b", re.I),
    "field": re.compile(r"\b(field|outdoor|in[- ]the[- ]wild|deployment|现场|户外)\b", re.I),
    "multi-robot": re.compile(r"\b(multi[- ]robot|multiagent|swarm|fleet|distributed|协同|多机器人)\b", re.I),
    "morphology": re.compile(r"\b(morphology|morphological|embodiment|body design|形态|仿生)\b", re.I),
    "clinical": re.compile(r"\b(clinical|patient|rehabilitation|assistive|medical|临床|康复)\b", re.I),
}
PACK_FILES = {name: f"pack-{name}.md" for name in PACK_RULES}

CONTRACT_PATTERNS = {
    "research_card": re.compile(r"research[ _-]?card", re.I),
    "experiment_contract": re.compile(r"experiment[ _-]?contract", re.I),
    "result_bundle": re.compile(r"result[ _-]?bundle", re.I),
    "claim_ledger": re.compile(r"claim[ _-]?ledger", re.I),
    "evidence_bundle": re.compile(r"evidence[ _-]?bundle", re.I),
    "target_fit_snapshot": re.compile(r"target[ _-]?fit[ _-]?snapshot", re.I),
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def review_folder_name() -> str:
    return "review-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M")


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def ignored(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    return any(part.lower() in IGNORE_DIRS or part.lower().startswith("_minted-") for part in rel.parts)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def include_names(source: str) -> list[str]:
    clean = re.sub(r"(?m)^\s*%.*$", "", source)
    return re.findall(r"\\(?:input|include|subfile)\s*\{([^}]+)\}", clean)


def resolve_candidates(raw: str, base: Path, root: Path, extensions: tuple[str, ...] = ()) -> tuple[Path | None, list[Path]]:
    raw = raw.strip()
    if not raw:
        return None, []
    raw_path = Path(raw)
    candidates = [base / raw_path]
    if raw_path.suffix == "":
        candidates.extend(base / (raw + ext) for ext in extensions)
    attempted: list[Path] = []
    for candidate in candidates:
        candidate = candidate.resolve()
        attempted.append(candidate)
        if candidate.is_file() and inside(candidate, root) and not ignored(candidate, root):
            return candidate, attempted
    return None, attempted


def resolve_ref(raw: str, base: Path, root: Path) -> Path | None:
    return resolve_candidates(raw, base, root, (".tex",))[0]


def include_graph(main: Path, root: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    found: list[Path] = []
    missing: list[dict[str, Any]] = []
    seen: set[Path] = set()
    queue = [main]
    while queue:
        current = queue.pop(0).resolve()
        if current in seen:
            continue
        seen.add(current)
        found.append(current)
        if current.suffix.lower() != ".tex":
            continue
        for raw in include_names(read_text(current)):
            child, attempted = resolve_candidates(raw, current.parent, root, (".tex",))
            if child is None:
                missing.append({"raw": raw, "from": str(current), "attempted": [str(p) for p in attempted]})
            else:
                queue.append(child)
    return found, missing


def locate_main(root: Path, explicit: str | None) -> Path:
    if explicit:
        path = (root / explicit).resolve() if not Path(explicit).is_absolute() else Path(explicit).resolve()
        if not path.is_file() or not inside(path, root):
            raise ValueError("explicit main file must be an existing file inside paper root")
        return path
    if root.is_file():
        return root.resolve()
    tex = [p for p in root.rglob("*.tex") if not ignored(p, root) and not EXCLUDED_NAMES.match(p.name)]
    candidates = [p for p in tex if "\\documentclass" in read_text(p) or "\\begin{document}" in read_text(p)]
    if len(candidates) == 1:
        return candidates[0].resolve()
    if len(candidates) > 1:
        scored = sorted(((len(include_names(read_text(p))), p) for p in candidates), reverse=True)
        if len(scored) == 1 or scored[0][0] > scored[1][0]:
            return scored[0][1].resolve()
        raise ValueError("multiple LaTeX main files are ambiguous; pass --main")
    docs = [p for p in root.rglob("*.md") if not ignored(p, root) and not EXCLUDED_NAMES.match(p.name)]
    if len(docs) == 1:
        return docs[0].resolve()
    raise ValueError("could not discover one manuscript main file; pass --main")


def referenced_files(files: list[Path], root: Path, pattern: re.Pattern[str], extensions: tuple[str, ...]) -> tuple[list[Path], list[dict[str, Any]]]:
    found: list[Path] = []
    missing: list[dict[str, Any]] = []
    for path in files:
        for match in pattern.finditer(read_text(path)):
            for raw in match.group(1).split(","):
                child, attempted = resolve_candidates(raw, path.parent, root, extensions)
                if child is None:
                    missing.append({"raw": raw.strip(), "from": str(path), "attempted": [str(p) for p in attempted]})
                elif child not in found:
                    found.append(child)
    return found, missing


def referenced_figures(files: list[Path], root: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    return referenced_files(
        files,
        root,
        re.compile(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^}]+)\}"),
        tuple(FIG_EXT),
    )


def bibliography_dependencies(files: list[Path], root: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    return referenced_files(
        files,
        root,
        re.compile(r"\\(?:bibliography|addbibresource)(?:\[[^]]*\])?\s*\{([^}]+)\}"),
        (".bib",),
    )


def extract_pdf_text(path: Path, max_chars: int = 120_000) -> dict[str, Any]:
    """在内存中抽取 PDF 文本供路由使用。

    Extract PDF text in memory for routing.  The source PDF remains the only
    allowed manuscript file; extracted text is bounded and is not written as a
    second manuscript artifact.
    """
    result: dict[str, Any] = {
        "status": "UNAVAILABLE",
        "tool": "pdftotext -layout",
        "char_count": 0,
        "text": "",
        "error": None,
    }
    if not path.is_file():
        result["status"] = "MISSING"
        result["error"] = "PDF file does not exist"
        return result
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        result["error"] = "pdftotext executable is unavailable"
        return result
    try:
        proc = subprocess.run(
            [pdftotext, "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        result["status"] = "FAILED"
        result["error"] = str(exc)
        return result
    if proc.returncode != 0:
        result["status"] = "FAILED"
        result["error"] = (proc.stderr or "pdftotext failed").strip()[:500]
        return result
    text = (proc.stdout or "").replace("\x00", "").strip()
    result["text"] = text[:max_chars]
    result["char_count"] = len(text)
    result["truncated"] = len(text) > max_chars
    result["status"] = "EXTRACTED" if text else "EMPTY"
    return result


def title_abstract(main: Path, pdf_text: str = "") -> tuple[str | None, str | None]:
    if main.suffix.lower() == ".pdf":
        if not pdf_text.strip():
            return None, None
        lines = [re.sub(r"\s+", " ", line).strip() for line in pdf_text.splitlines() if line.strip()]
        title = None
        explicit_title = next((line.split(":", 1)[1].strip() for line in lines[:20] if re.match(r"^title\s*:", line, re.I)), None)
        if explicit_title:
            title = explicit_title
        else:
            for line in lines[:25]:
                if len(line) <= 240 and not re.match(r"^(?:arxiv|preprint|abstract|keywords?|author|\d+\s+introduction)\b", line, re.I):
                    title = line
                    break
        abstract = None
        abstract_match = re.search(
            r"(?is)\babstract\b\s*[:.]?\s*(.+?)(?=\n\s*(?:1\.?\s+)?(?:introduction|keywords?)\b|\Z)",
            pdf_text,
        )
        if abstract_match:
            abstract = re.sub(r"\s+", " ", abstract_match.group(1)).strip()
        return title, abstract
    source = read_text(main)
    if main.suffix.lower() == ".md":
        lines = source.splitlines()
        return next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), None), None
    title_match = re.search(r"\\title\s*\{([^}]*)\}", source, re.S)
    abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", source, re.S)
    return (
        title_match.group(1).strip() if title_match else None,
        abstract_match.group(1).strip() if abstract_match else None,
    )


def artifact_record(path: Path, role: str, reason: str, exists: bool | None = None) -> dict[str, Any]:
    path = path.resolve()
    if exists is None:
        exists = path.is_file()
    if not exists:
        return {
            "path": str(path),
            "role": role,
            "exists": False,
            "sha256": None,
            "size_bytes": None,
            "mtime_utc": None,
            "discovery_reason": reason,
        }
    stat = path.stat()
    return {
        "path": str(path),
        "role": role,
        "exists": True,
        "sha256": sha256_file(path),
        "size_bytes": stat.st_size,
        "mtime_utc": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "discovery_reason": reason,
    }


def state_record(paths: list[Path], kind: str, root: Path) -> dict[str, Any]:
    if not paths:
        return {
            "state": "NOT_FOUND",
            "path": None,
            "search_locations": [str(root)],
            "note": f"No {kind} was discovered under the manuscript root.",
        }
    if len(paths) > 1:
        return {
            "state": "AMBIGUOUS",
            "path": None,
            "search_locations": [str(p) for p in paths],
            "note": f"Multiple {kind} candidates were found; select one explicitly.",
        }
    return {
        "state": "FOUND",
        "path": str(paths[0]),
        "search_locations": [str(root)],
        "note": f"Discovered {kind} inside the allowed manuscript root.",
    }


def normalized_name(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", " ", path.name.lower()).strip()


def discover_contracts(root: Path, explicit: list[Path] | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, list[Path]]]:
    candidates: dict[str, list[Path]] = {key: [] for key in CONTRACT_PATTERNS}
    # Never recursively inspect an arbitrary parent workspace.  Automatic
    # discovery is limited to the manuscript root and a few explicitly named
    # contract directories.  A PDF-only review can opt in with --artifact.
    candidate_dirs = [root]
    for name in ("contracts", "scientific-contracts", "evidence", "artifacts"):
        directory = root / name
        if directory.is_dir():
            candidate_dirs.append(directory)
    for directory in candidate_dirs:
        for path in directory.glob("*.json"):
            if ignored(path, root):
                continue
            name = normalized_name(path)
            for key, pattern in CONTRACT_PATTERNS.items():
                if pattern.search(name) and path.resolve() not in candidates[key]:
                    candidates[key].append(path.resolve())
    for path in explicit or []:
        path = path.resolve()
        if not inside(path, root):
            continue
        name = normalized_name(path)
        for key, pattern in CONTRACT_PATTERNS.items():
            if pattern.search(name) and path not in candidates[key]:
                candidates[key].append(path)
    records = {key: state_record(value, key, root) for key, value in candidates.items()}
    return records, candidates


def parse_json(path: Path) -> Any | None:
    try:
        return load_json(path)
    except (OSError, ValueError, JsonIntegrityError):
        return None


def check_claim_ledger_reference(ledger: Path | None, result_candidates: list[Path]) -> list[str]:
    if ledger is None or not ledger.is_file():
        return []
    data = parse_json(ledger)
    if not isinstance(data, dict):
        return [f"Claim Ledger could not be parsed: {ledger}"]
    ref = data.get("result_bundle")
    if not isinstance(ref, dict) or not ref.get("id"):
        return []
    expected = str(ref["id"])
    found_ids: set[str] = set()
    for candidate in result_candidates:
        payload = parse_json(candidate)
        if isinstance(payload, dict):
            value = payload.get("bundle_id") or payload.get("result_bundle_id") or payload.get("id")
            if value:
                found_ids.add(str(value))
    if expected not in found_ids:
        return [f"Claim Ledger references absent Result Bundle ID {expected!r}"]
    return []


def filename_warnings(paths: list[Path]) -> list[str]:
    warnings: list[str] = []
    by_name: dict[str, list[Path]] = {}
    for path in paths:
        by_name.setdefault(path.name.lower(), []).append(path)
        if re.search(r"\s", path.name) or re.search(r"[^A-Za-z0-9._-]", path.name):
            warnings.append(f"Irregular filename may break tooling: {path.name}")
    for name, duplicates in by_name.items():
        if len(duplicates) > 1:
            warnings.append("Duplicate basename across dependencies: " + ", ".join(str(p) for p in duplicates))
    return sorted(set(warnings))


def pdf_preflight(path: Path, text_extraction: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "status": "UNAVAILABLE",
        "page_count": None,
        "page_size": None,
        "font_inventory": None,
        "missing_embeds": None,
        "unresolved_references": None,
        "text_extraction": {
            key: value
            for key, value in (text_extraction or {}).items()
            if key != "text"
        },
        "compilation_timestamp": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if path.is_file() else None,
        "checked_at": utc_now(),
    }
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        try:
            proc = subprocess.run([pdfinfo, str(path)], capture_output=True, text=True, timeout=10, check=False)
            if proc.returncode == 0:
                facts: dict[str, str] = {}
                for line in proc.stdout.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        facts[key.strip()] = value.strip()
                result.update({"status": "VERIFIED", "page_count": facts.get("Pages"), "page_size": facts.get("Page size")})
                pdffonts = shutil.which("pdffonts")
                if pdffonts:
                    font_proc = subprocess.run([pdffonts, str(path)], capture_output=True, text=True, timeout=10, check=False)
                    rows = []
                    missing = []
                    if font_proc.returncode == 0:
                        for line in font_proc.stdout.splitlines():
                            if line.startswith("name ") or line.startswith("-" ) or not line.strip():
                                continue
                            fields = line.split()
                            if len(fields) >= 7:
                                rows.append({"name": fields[0], "type": fields[1], "emb": fields[2], "sub": fields[3]})
                                if fields[2].lower() not in {"yes", "y"}:
                                    missing.append(fields[0])
                        result["font_inventory"] = rows
                        result["missing_embeds"] = missing
                    else:
                        result["font_inventory"] = "UNAVAILABLE"
                        result["missing_embeds"] = "UNAVAILABLE"
                else:
                    result["font_inventory"] = "UNAVAILABLE"
                    result["missing_embeds"] = "UNAVAILABLE"
                result["unresolved_references"] = "UNVERIFIED"
            else:
                result["status"] = "FAILED"
                result["error"] = proc.stderr.strip()[:500]
        except (OSError, subprocess.SubprocessError) as exc:
            result["status"] = "FAILED"
            result["error"] = str(exc)
    return result


def detect_claim_shape(source: str) -> dict[str, bool]:
    patterns = {
        "embodied_system": r"\b(robot|embodied|hardware|real[- ]robot|physical)\b",
        "learning": r"\b(learn|policy|training|dataset|reinforcement|imitation)\b",
        "mechanism": r"\b(mechanism|ablation|causal|channel|factor|component|why)\b",
        "human": r"\b(human|participant|user|hri|shared control)\b",
        "soft_material": r"\b(soft|compliant|elastomer|continuum|deformable)\b",
        "practice": r"\b(deployment|field|industrial|safety|factory|workflow)\b",
        "cross_context": r"\b(generaliz|transfer|cross[- ]domain|multiple tasks|different environments)\b",
    }
    return {key: bool(re.search(pattern, source, re.I)) for key, pattern in patterns.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paper_root", type=Path, help="待审 PDF，或只包含待审 LaTeX 工程的工作区")
    parser.add_argument("--main")
    parser.add_argument("--review-id")
    parser.add_argument("--language", help="评审输出语言：任意单语标签，或 en+任意语言；必须显式提供")
    parser.add_argument("--artifact", action="append", default=[], help="可选的、位于待审根目录内的显式合同/证据 JSON")
    parser.add_argument("--output", help="默认写入 reviews/review-<timestamp>/jsons/review-context.json")
    args = parser.parse_args()
    try:
        output_language = normalize_language(args.language)
    except ValueError as exc:
        raise SystemExit(str(exc))

    input_path = args.paper_root.resolve()
    if input_path.is_file() and input_path.suffix.lower() not in {".pdf", ".tex"}:
        raise SystemExit("review input must be a PDF file or a LaTeX workspace")
    root = input_path.parent if input_path.is_file() else input_path
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        main_file = input_path
        files, missing_includes = [main_file], []
    else:
        main_file = locate_main(root, args.main)
        files, missing_includes = include_graph(main_file, root)
    figures, missing_figures = referenced_figures(files, root)
    bibliography, missing_bibliography = bibliography_dependencies(files, root)

    all_files = list(files)
    for path in figures + bibliography:
        if path not in all_files:
            all_files.append(path)
    table_candidates = [p for p in files if "table" in p.name.lower() or any(part.lower() in {"table", "tables"} for part in p.parts)]
    for table_dir_name in ("table", "tables"):
        table_dir = root / table_dir_name
        if table_dir.is_dir():
            table_candidates.extend(p for p in table_dir.glob("*") if p.is_file() and not ignored(p, root))
    table_candidates = list(dict.fromkeys(table_candidates))
    for path in table_candidates:
        if path not in all_files:
            all_files.append(path)

    contract_states, contract_candidates = discover_contracts(root, [Path(path) for path in args.artifact])
    contract_paths = {key: paths[0] for key, paths in contract_candidates.items() if len(paths) == 1}
    for paths in contract_candidates.values():
        for path in paths:
            if path not in all_files:
                all_files.append(path)

    # Include supplementary materials only when their directory is explicitly named;
    # do not accidentally expose an entire research workspace to reviewers.
    supplementary = []
    for directory_name in ("supplementary", "supplement", "appendix"):
        directory = root / directory_name
        if directory.is_dir():
            supplementary.extend(p for p in directory.rglob("*") if p.is_file() and not ignored(p, root))
    supplementary = list(dict.fromkeys(supplementary))
    for path in supplementary:
        if path not in all_files:
            all_files.append(path)

    # A compiled manuscript PDF at the workspace root is an explicit review
    # artifact; do not recursively search arbitrary build/output directories.
    if input_path.is_dir():
        for path in root.glob("*.pdf"):
            if path.is_file() and path.resolve() not in figures and path.resolve() not in all_files:
                all_files.append(path.resolve())

    rendered_assets = [p for p in all_files if p.suffix.lower() == ".pdf" and p not in figures]
    pdf_text_extraction = extract_pdf_text(main_file) if main_file.suffix.lower() == ".pdf" else {"status": "NOT_APPLICABLE", "tool": None, "char_count": 0, "text": "", "error": None}
    all_text = "\n".join(read_text(path) for path in files if path.suffix.lower() in {".tex", ".md", ".txt"})
    if pdf_text_extraction.get("text"):
        all_text = str(pdf_text_extraction["text"]) + "\n" + all_text
    for path in contract_paths.values():
        all_text += "\n" + read_text(path)
    title, abstract = title_abstract(main_file, str(pdf_text_extraction.get("text") or ""))

    artifact_records: dict[str, dict[str, Any]] = {}
    def add_record(path: Path, role: str, reason: str) -> None:
        artifact_records[str(path.resolve())] = artifact_record(path, role, reason)

    for path in files:
        add_record(path, "manuscript", "LaTeX/Markdown main file or transitive include dependency")
    for path in figures:
        add_record(path, "figure", "Referenced by an includegraphics command")
    for path in bibliography:
        add_record(path, "bibliography", "Referenced by bibliography/addbibresource command")
    for path in table_candidates:
        add_record(path, "table", "Table file or table directory dependency")
    for path in supplementary:
        add_record(path, "supplementary", "Located below an explicitly named supplementary directory")
    for path in all_files:
        if path.suffix.lower() == ".pdf" and path not in figures and path not in files:
            add_record(path, "compiled_artifact", "PDF located at the explicit LaTeX workspace root")
    for key, paths in contract_candidates.items():
        for path in paths:
            role = "target_fit_snapshot" if key == "target_fit_snapshot" else ("evidence_bundle" if key == "evidence_bundle" else "contract")
            add_record(path, role, f"Filename matches {key} contract pattern")

    # Preserve unresolved references as first-class manifest entries.
    missing_records: list[dict[str, Any]] = []
    for group, entries, role in (
        ("latex_include_graph", missing_includes, "manuscript"),
        ("rendered_asset_dependencies", missing_figures, "figure"),
        ("bibliography_dependencies", missing_bibliography, "bibliography"),
    ):
        for item in entries:
            attempted = item.get("attempted") or []
            if attempted:
                missing_records.append(artifact_record(Path(attempted[0]), role, f"Unresolved {group} reference: {item.get('raw')}", exists=False))

    target_snapshot: dict[str, Any] = dict(contract_states["target_fit_snapshot"])
    target_path = contract_paths.get("target_fit_snapshot")
    if target_path:
        payload = parse_json(target_path)
        if isinstance(payload, dict):
            target_snapshot.update(payload)
            target_snapshot["state"] = "FOUND"
            target_snapshot["path"] = str(target_path)
            target_snapshot.setdefault("policy_coverage", {})
            target_snapshot.setdefault("refresh_state", "OFFICIAL_SOURCE_MISSING" if not payload.get("sources") else "NOT_NEEDED")
    else:
        target_snapshot.update({"target": None, "article_type": None, "official_sources": [], "policy_coverage": {}, "refresh_state": "OFFICIAL_SOURCE_MISSING", "checked_at": None, "expires_at": None})

    warnings = filename_warnings([Path(item["path"]) for item in artifact_records.values() if item["exists"]])
    warnings.extend(check_claim_ledger_reference(contract_paths.get("claim_ledger"), contract_candidates.get("result_bundle", [])))
    warnings.extend(f"Missing dependency reference: {item['path']}" for item in missing_records)
    if main_file.suffix.lower() == ".pdf" and pdf_text_extraction.get("status") != "EXTRACTED":
        warnings.append("PDF_TEXT_UNAVAILABLE: title, abstract and domain-pack detection may be incomplete")

    detected_packs = [name for name, pattern in PACK_RULES.items() if pattern.search(all_text)]
    pack_root = Path(__file__).resolve().parents[1] / "references"
    activated_packs = [name for name in detected_packs if (pack_root / PACK_FILES[name]).is_file()]
    missing_packs = [name for name in detected_packs if not (pack_root / PACK_FILES[name]).is_file()]
    pack_registry = {
        "detected": detected_packs,
        "activated": activated_packs,
        "missing": missing_packs,
        "library_root": str(pack_root),
        "notes": {name: "activated by manuscript/contract signal" for name in activated_packs},
    }

    compiled = [pdf_preflight(path, pdf_text_extraction if path.resolve() == main_file.resolve() else None) for path in rendered_assets if path.is_file()]
    source_language = "zh-en" if re.search(r"[\u3400-\u9fff]", all_text) and re.search(r"[A-Za-z]", all_text) else ("zh" if re.search(r"[\u3400-\u9fff]", all_text) else ("en" if all_text else "unknown"))
    review_id = args.review_id or "REV-" + utc_now().replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")
    dependency_graphs = {
        "latex_include_graph": [str(path) for path in files],
        "bibliography_dependencies": [str(path) for path in bibliography],
        "rendered_asset_dependencies": [str(path) for path in rendered_assets],
        "scientific_contract_dependencies": [str(path) for key, path in contract_paths.items() if key != "target_fit_snapshot"],
        "evidence_bundle_dependencies": [str(path) for key, paths in contract_candidates.items() if key == "evidence_bundle" for path in paths],
    }
    allowed = sorted(path for path, item in artifact_records.items() if item["exists"])
    context = {
        "schema_version": "robotics-review-context.v1",
        "review_id": review_id,
        "review_output_dir": None,
        "mode": "full",
        "created_at": utc_now(),
        "paper": {
            "root": str(root),
            "main_file": str(main_file),
            "include_graph": [str(p) for p in files],
            "figure_files": [str(p) for p in figures],
            "table_files": [str(p) for p in table_candidates],
            "bibliography_files": [str(p) for p in bibliography],
            "supplementary_files": [str(p) for p in supplementary],
            "language": source_language,
            "output_language": output_language,
            "title": title,
            "abstract": abstract,
            "pdf_text_extraction": {key: value for key, value in pdf_text_extraction.items() if key != "text"},
        },
        "scope_guard": {
            "allowed_files": allowed,
            "ignored_patterns": ["**/reviews/**", "**/old/**", "**/archive/**", "**/*response*", "**/*letter*", "**/README*"],
            "untrusted_materials": True,
        },
        "artifact_manifest": sorted(list(artifact_records.values()) + missing_records, key=lambda item: item["path"]),
        "dependency_graphs": dependency_graphs,
        "discovery_warnings": sorted(set(warnings)),
        "compiled_artifact_preflight": compiled,
        "target_fit_snapshot": target_snapshot,
        "review_language": output_language,
        "review_language_mode": language_mode(output_language),
        "scientific_contract": {key: contract_states[key] for key in ("research_card", "experiment_contract", "result_bundle", "claim_ledger", "evidence_bundle")},
        "claim_shape": detect_claim_shape(all_text),
        "domain_packs": activated_packs,
        "domain_pack_registry": pack_registry,
        "reviewer_configuration": list(REVIEWERS),
        "status": "DISCOVERED",
    }
    if args.output:
        output = Path(args.output).resolve()
        if output.parent.name != "jsons" or not output.parent.parent.name.startswith("review-") or not inside(output, root / "reviews"):
            raise SystemExit("review outputs must be stored under reviews/review-<timestamp>/jsons")
        review_dir = output.parent.parent
    else:
        base = root / "reviews" / review_folder_name()
        review_dir = base
        suffix = 2
        while review_dir.exists():
            review_dir = root / "reviews" / f"{base.name}-{suffix:02d}"
            suffix += 1
        output = review_dir / "jsons" / "review-context.json"
    context["review_output_dir"] = str(review_dir.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    (review_dir / "markdowns").mkdir(parents=True, exist_ok=True)
    write_json(output, context)
    print(str(output))


if __name__ == "__main__":
    main()
