#!/usr/bin/env python3
"""Fetch public paper sources into an ignored cache and write an auditable manifest.

The corpus index is intentionally metadata-only.  This helper keeps downloaded
PDFs outside the tracked JSON contracts and records only provenance, resolution
status, byte counts, and hashes in the manifest.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / "corpus" / "public-paper-index.json"
DEFAULT_CACHE = ROOT / "corpus" / "papers"
DEFAULT_MANIFEST = ROOT / "corpus" / "public-paper-fulltext-manifest.v1.json"
DEFAULT_OVERRIDES = ROOT / "corpus" / "public-paper-source-overrides.v1.json"
USER_AGENT = "Robotics-Research-Skill/1.0 public-corpus-audit"
MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_PDF_BYTES = 80 * 1024 * 1024


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_pdf(data: bytes, content_type: str) -> bool:
    return data.startswith(b"%PDF-") or "application/pdf" in content_type.lower()


def arxiv_pdf_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() != "arxiv.org":
        return None
    match = re.search(r"/(?:abs|pdf|html)/([^/?#]+)", parsed.path)
    if not match:
        return None
    identifier = match.group(1)
    if identifier.endswith(".pdf"):
        identifier = identifier[:-4]
    return f"https://arxiv.org/pdf/{identifier}.pdf"


def candidate_urls(record: dict, override_urls: list[str] | None = None) -> list[str]:
    candidates: list[str] = []
    candidates.extend(override_urls or [])
    for field in ("preprint", "final_publication"):
        entry = record.get(field) or {}
        url = entry.get("url") if isinstance(entry, dict) else None
        if not isinstance(url, str) or not url:
            continue
        derived = arxiv_pdf_url(url)
        if derived:
            candidates.append(derived)
        candidates.append(url)
    output: list[str] = []
    for url in candidates:
        if url not in output:
            output.append(url)
    return output


def request_bytes(url: str) -> tuple[str, int | None, str, bytes, str | None]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,text/html;q=0.8,*/*;q=0.1"})
    try:
        with urlopen(request, timeout=35) as response:
            content_type = response.headers.get("Content-Type", "")
            status = getattr(response, "status", None)
            data = response.read(MAX_PDF_BYTES + 1)
            if len(data) > MAX_PDF_BYTES:
                return "TOO_LARGE", status, content_type, b"", "response exceeds 80 MiB limit"
            return "FETCHED", status, content_type, data, None
    except HTTPError as exc:
        return "HTTP_ERROR", exc.code, exc.headers.get("Content-Type", ""), b"", str(exc)
    except (URLError, TimeoutError, OSError) as exc:
        return "FETCH_ERROR", None, "", b"", str(exc)


def html_pdf_links(base_url: str, data: bytes) -> list[str]:
    text = data[:MAX_HTML_BYTES].decode("utf-8", errors="ignore")
    links = re.findall(r"(?:href|data-download-url)=[\"']([^\"']+)[\"']", text, flags=re.I)
    scored: list[tuple[int, str]] = []
    for link in links:
        absolute = urljoin(base_url, link)
        lower = absolute.lower()
        if any(token in lower for token in (".pdf", "/pdf", "download", "fulltext", "accepted")):
            score = 0
            if ".pdf" in lower:
                score += 4
            if "/pdf" in lower:
                score += 2
            if "download" in lower or "fulltext" in lower:
                score += 1
            scored.append((-score, absolute))
    return [url for _, url in sorted(set(scored))[:5]]


def fetch_record(record: dict, cache_dir: Path, overrides: dict[str, list[dict]]) -> dict:
    paper_id = record["paper_id"]
    override_urls = [item["url"] for item in overrides.get(paper_id, []) if isinstance(item, dict) and item.get("url")]
    attempted: list[str] = []
    errors: list[str] = []
    checked_at = now()
    for url in candidate_urls(record, override_urls):
        if url in attempted:
            continue
        attempted.append(url)
        status, http_status, content_type, data, error = request_bytes(url)
        if status == "FETCHED" and is_pdf(data, content_type):
            target = cache_dir / f"{paper_id}.pdf"
            target.write_bytes(data)
            return {
                "paper_id": paper_id,
                "title": record.get("title"),
                "status": "DOWNLOADED",
                "source_url": url,
                "source_override": url in override_urls,
                "source_kind": (record.get("preprint") or {}).get("kind"),
                "final_publication_url": (record.get("final_publication") or {}).get("url"),
                "checked_at": checked_at,
                "retrieved_at": now(),
                "http_status": http_status,
                "content_type": content_type,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
                "local_path": str(target.relative_to(ROOT)),
                "attempted_urls": attempted,
                "resolution_note": "public PDF source; cache is ignored by Git",
            }
        if status == "FETCHED" and "html" in content_type.lower():
            for link in html_pdf_links(url, data):
                if link in attempted:
                    continue
                attempted.append(link)
                link_status, link_http, link_type, link_data, link_error = request_bytes(link)
                if link_status == "FETCHED" and is_pdf(link_data, link_type):
                    target = cache_dir / f"{paper_id}.pdf"
                    target.write_bytes(link_data)
                    return {
                        "paper_id": paper_id,
                        "title": record.get("title"),
                        "status": "DOWNLOADED",
                        "source_url": link,
                        "source_override": link in override_urls,
                        "landing_url": url,
                        "source_kind": (record.get("preprint") or {}).get("kind"),
                        "final_publication_url": (record.get("final_publication") or {}).get("url"),
                        "checked_at": checked_at,
                        "retrieved_at": now(),
                        "http_status": link_http,
                        "content_type": link_type,
                        "bytes": len(link_data),
                        "sha256": sha256_bytes(link_data),
                        "local_path": str(target.relative_to(ROOT)),
                        "attempted_urls": attempted,
                        "resolution_note": "PDF resolved from a public landing page; cache is ignored by Git",
                    }
                if link_error:
                    errors.append(f"{link}: {link_error}")
        if error:
            errors.append(f"{url}: {error}")

    return {
        "paper_id": paper_id,
        "title": record.get("title"),
        "status": "UNRESOLVED",
        "source_url": (record.get("preprint") or {}).get("url"),
        "source_override": False,
        "source_kind": (record.get("preprint") or {}).get("kind"),
        "final_publication_url": (record.get("final_publication") or {}).get("url"),
        "checked_at": checked_at,
        "retrieved_at": None,
        "http_status": None,
        "content_type": None,
        "bytes": 0,
        "sha256": None,
        "local_path": None,
        "attempted_urls": attempted,
        "resolution_note": "No public PDF resolved automatically; manual source verification required",
        "errors": errors[:8],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    overrides = {}
    if args.overrides.exists():
        overrides = json.loads(args.overrides.read_text(encoding="utf-8")).get("records", {})
    records = index["records"][: args.limit]
    if not args.dry_run:
        args.cache_dir.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        results = [
            {
                "paper_id": r["paper_id"],
                "title": r.get("title"),
                "status": "NOT_RUN",
                "source_url": (r.get("preprint") or {}).get("url"),
                "final_publication_url": (r.get("final_publication") or {}).get("url"),
                "attempted_urls": candidate_urls(r, [item["url"] for item in overrides.get(r["paper_id"], [])]),
            }
            for r in records
        ]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            results = list(pool.map(lambda r: fetch_record(r, args.cache_dir, overrides), records))
    results.sort(key=lambda item: item["paper_id"])
    manifest = {
        "schema_version": "robotics-public-paper-fulltext-manifest.v1",
        "generated_at": now(),
        "source_index": display_path(args.index),
        "cache_policy": "PDFs are local ignored cache; manifest contains provenance and hashes only",
        "record_count": len(results),
        "status_counts": {status: sum(1 for item in results if item["status"] == status) for status in sorted({item["status"] for item in results})},
        "records": results,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(args.manifest), "record_count": len(results), "status_counts": manifest["status_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
