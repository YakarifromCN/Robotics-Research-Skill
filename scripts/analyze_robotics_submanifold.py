#!/usr/bin/env python3
"""分析机器人研究子流形并生成 venue 因子候选。 / Analyze robotics submanifold fit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.robotics_submanifold import analyze, load_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", help="project profile or V2 research-card JSON")
    parser.add_argument("--catalog", default=str(ROOT / "corpus" / "venue-catalog.v1.json"))
    parser.add_argument("--model", default=str(ROOT / "corpus" / "robotics-submanifold.v1.json"))
    parser.add_argument("--output")
    parser.add_argument("--top-k", type=int, default=12)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    profile = load_json(args.profile)
    catalog = load_json(args.catalog)
    model = load_json(args.model)
    result = analyze(profile, catalog, model, top_k=args.top_k)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        print(Path(args.output).resolve())
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
