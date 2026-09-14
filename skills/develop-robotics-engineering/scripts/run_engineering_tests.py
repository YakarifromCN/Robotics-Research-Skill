#!/usr/bin/env python3
"""执行冻结测试，清理超时进程组并保留有界日志。

Execute frozen tests with process-group cleanup and bounded logs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import signal
import subprocess
import time
from validate_engineering_artifacts import load_frontmatter


def execute(row, workspace, timeout=300, limit=65536):
    """不调用隐式 shell，不修改全局环境。 / No implicit shell or global environment changes."""
    if timeout <= 0 or limit < 0:
        raise ValueError("timeout must be positive and output limit nonnegative")
    env = dict(os.environ) if row.get("inherit_env", True) else {}
    for key in row.get("unset_env", []):
        env.pop(key, None)
    argv = shlex.split(row["command"])
    while argv and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*=.*", argv[0]):
        key, value = argv.pop(0).split("=", 1)
        env[key] = value
    if "argv" in row and row["argv"] != argv:
        raise ValueError("argv differs from the frozen command")
    env.update({str(k): str(v) for k, v in row.get("env", {}).items()})
    if not argv or any(not isinstance(arg, str) for arg in argv):
        raise ValueError("test argv must be a nonempty string list")
    cwd = (workspace / row.get("cwd", ".")).resolve()
    cwd.relative_to(workspace.resolve())
    if os.name != "posix":
        raise ValueError("process-tree cleanup requires a POSIX host")
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    hashes = {key: hashlib.sha256() for key in streams}
    truncated = timed_out = False
    deadline = time.monotonic() + timeout
    selector = selectors.DefaultSelector()
    for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
        selector.register(stream, selectors.EVENT_READ, name)
    try:
        while selector.get_map():
            if time.monotonic() >= deadline:
                timed_out = True
                break
            for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                hashes[key.data].update(chunk)
                remaining = max(0, limit - len(streams[key.data]))
                streams[key.data].extend(chunk[:remaining])
                truncated |= len(chunk) > remaining
        if not timed_out:
            try:
                process.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                timed_out = True
    finally:
        # 只清理本次创建的进程组。 / Clean only this launch's process group.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
        process.wait()
        selector.close()
        process.stdout.close()
        process.stderr.close()
    return {"exit_code": process.returncode, "timed_out": timed_out, "output_truncated": truncated,
            **{f"{key}_sha256": value.hexdigest() for key, value in hashes.items()},
            **{key: bytes(value).decode("utf-8", errors="replace") for key, value in streams.items()}}


def run(task_path: Path, workspace: Path, timeout: int = 300) -> list[dict]:
    task, _ = load_frontmatter(task_path)
    rows = task.get("tests")
    if not isinstance(rows, list) or len(rows) > 3:
        raise ValueError("Task tests must contain 0-3 frozen commands")
    receipts = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("command"), str) or not row["command"].strip():
            raise ValueError("each test requires its frozen command")
        try:
            result = execute(row, workspace, timeout)
        except (OSError, ValueError) as exc:
            result = {"exit_code": None, "timed_out": False, "error": str(exc), "executed": False}
        bound = {"command": row["command"], "result": "PASS" if result["exit_code"] == 0 and not result["timed_out"] else "FAIL", "exit_code": result["exit_code"]}
        receipts.append({**result, **bound, "executed": result.get("executed", True),
                         "receipt_sha256": hashlib.sha256(json.dumps(bound, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                         "runner": "run_engineering_tests.py"})
    return receipts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", type=Path)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    try:
        receipts = run(args.task, args.workspace.resolve(), args.timeout)
        payload = {"schema_version": "robotics-engineering-test-receipts.v1", "tests": receipts}
    except (ValueError, OSError) as exc:
        payload = {"valid": False, "error": str(exc)}
        receipts = [{"result": "FAIL"}]
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if all(row["result"] == "PASS" for row in receipts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
