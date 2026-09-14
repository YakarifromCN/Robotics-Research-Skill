#!/usr/bin/env python3
"""生成和规范化工程工件，不推断执行结果。 / Generate and normalize artifacts without inferring results."""
import argparse
import json
from pathlib import Path
from validate_engineering_artifacts import load_frontmatter, task_contract_sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("init", "normalize", "hash"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data, body = load_frontmatter(args.input)
    if args.action == "hash":
        print(json.dumps({"task_contract_sha256": task_contract_sha256(data)}))
        return 0
    if args.action == "init":
        for field in ("task_id", "original_request", "allowed_paths", "tests", "stop_conditions", "steps"):
            if field not in data:
                raise ValueError(f"missing {field}; provide the authorized task value")
        if len(data["tests"]) > 3 or not 3 <= len(data["steps"]) <= 7:
            raise ValueError("Task requires 3-7 steps and 0-3 tests")
        data = {**data, "artifact": "TASK"}
    data["body"] = body
    output = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    if args.output:
        # 不覆盖冻结输入或已有工件。 / Never overwrite frozen input or existing artifacts.
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(output)
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
