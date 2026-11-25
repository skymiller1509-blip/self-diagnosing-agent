"""Self-Diagnosing Agent, built on the real OpenMinion 0.1 Python SDK.

One workflow, end to end:
  1. read the numbers file,
  2. sum it,
  3. if the sum fails, diagnose the failure in plain language,
  4. apply the recommended fix (quarantine the bad lines),
  5. retry the sum and write the total.

The model drives every tool call through `openminion.Agent`. The tools below
are real `@tool` functions; the diagnosis logic lives in `diagnosis.py` so
it can be tested without a model.

Every tool invocation is recorded (success and failure) in
`runs/latest/tool_calls.jsonl`, so the demo can verify each step.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


def _sanitize_proxy_env() -> None:
    """Strip bracketed IPv6 entries from NO_PROXY.

    This VM's NO_PROXY contains entries like `[::1]` and
    `[fd8b:...::1]`. httpx (used by the OpenMinion provider client)
    cannot parse those and fails with `InvalidURL: Invalid port`.
    Unbracketing them keeps the same hosts while letting httpx work.
    Must run before any httpx client is created.
    """
    for key in ("NO_PROXY", "no_proxy"):
        value = os.environ.get(key)
        if not value:
            continue
        parts = [
            p[1:-1] if p.startswith("[") and p.endswith("]") else p
            for p in value.split(",")
        ]
        os.environ[key] = ",".join(parts)


_sanitize_proxy_env()

from openminion import Agent, ProviderError, tool

from self_diagnosing_agent.diagnosis import diagnose, diagnosis_to_text, parse_numbers

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "numbers.txt"
OUT_DIR = BASE_DIR / "out"
TOTAL_FILE = OUT_DIR / "total.txt"
QUARANTINED_FILE = OUT_DIR / "quarantined.txt"

# JSONL transcript of every real tool execution, for the demo record.
TRANSCRIPT_PATH = BASE_DIR / "runs" / "latest" / "tool_calls.jsonl"


def _log_tool(name: str, args: dict, status: str, result: str) -> None:
    TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": time.strftime("%H:%M:%S"),
        "tool": name,
        "args": args,
        "status": status,
        "result": result[:500],
    }
    with TRANSCRIPT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"  [tool] {name}({json.dumps(args)}) [{status}] -> {result[:200]}")


def _check_path(path: str) -> Path:
    full = (BASE_DIR / path).resolve()
    if not str(full).startswith(str(BASE_DIR)):
        raise ValueError("path escapes the project directory")
    if not full.exists():
        # The model sometimes absolutises a relative path against the
        # OpenMinion home dir (e.g. .../.openminion-home/data/numbers.txt).
        # Fall back to the known project-relative file with the same suffix.
        normalised = str(path).replace("\\", "/")
        for suffix in ("data/numbers.txt", "out/total.txt", "out/quarantined.txt"):
            if normalised.endswith(suffix):
                return (BASE_DIR / suffix).resolve()
    return full


@tool(min_scope="READ_ONLY", idempotent=True)
def read_numbers(path: str = "data/numbers.txt") -> str:
    """Read a numbers file, one number per line. Returns lines with numbers."""
    try:
        full = _check_path(path)
        lines = full.read_text(encoding="utf-8").splitlines()
        result = "\n".join(
            f"line {i}: {line}" for i, line in enumerate(lines, start=1)
        )
    except Exception as exc:  # noqa: BLE001 - record and re-raise
        _log_tool("read_numbers", {"path": path}, "error", str(exc))
        raise
    _log_tool("read_numbers", {"path": path}, "ok", result)
    return result


@tool(min_scope="READ_ONLY", idempotent=True)
def sum_numbers(path: str = "data/numbers.txt") -> str:
    """Add up all numbers in a file. Fails loudly on the first bad line."""
    try:
        full = _check_path(path)
        numbers, bad = parse_numbers(full)
        if bad:
            first = bad[0]
            raise ValueError(
                f"line {first.line_number}: '{first.text}' is not a number"
            )
        total = sum(numbers)
        result = f"total: {total:g} from {len(numbers)} numbers"
    except Exception as exc:  # noqa: BLE001 - record and re-raise
        _log_tool("sum_numbers", {"path": path}, "error", str(exc))
        raise
    _log_tool("sum_numbers", {"path": path}, "ok", result)
    return result


@tool(min_scope="READ_ONLY", idempotent=True)
def diagnose_failure(error: str = "") -> str:
    """Explain in plain language why the last sum failed, and recommend a fix.

    Call with no arguments: it reads the most recent failure from the run
    log (runs/latest/tool_calls.jsonl), so the exact error text is never
    retyped by hand. Pass an error string only to diagnose a specific
    message instead.
    """
    try:
        if not error:
            error = _last_error() or "no failure recorded"
        full = _check_path("data/numbers.txt")
        d = diagnose(full)
        result = (
            f"The failed call reported: {error}\n"
            f"My diagnosis:\n{diagnosis_to_text(d)}"
        )
    except Exception as exc:  # noqa: BLE001 - record and re-raise
        _log_tool("diagnose_failure", {"error": error}, "error", str(exc))
        raise
    _log_tool("diagnose_failure", {"error": error}, "ok", result)
    return result


def _last_error() -> str:
    """Return the result of the most recent failed tool call, if any."""
    if not TRANSCRIPT_PATH.exists():
        return ""
    for line in reversed(TRANSCRIPT_PATH.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("status") == "error":
            return str(entry.get("result", ""))
    return ""


@tool
def quarantine_bad_lines(path: str = "data/numbers.txt") -> str:
    """Move bad lines out of a numbers file into out/quarantined.txt.

    Keeps only the valid numbers, so the sum can be retried.
    """
    try:
        full = _check_path(path)
        numbers, bad = parse_numbers(full)
        if not bad:
            result = "No bad lines. Nothing to quarantine."
            _log_tool("quarantine_bad_lines", {"path": path}, "ok", result)
            return result
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        QUARANTINED_FILE.write_text(
            "\n".join(f"line {b.line_number}: {b.text}" for b in bad) + "\n",
            encoding="utf-8",
        )
        full.write_text(
            "\n".join(f"{n:g}" for n in numbers) + "\n", encoding="utf-8"
        )
        result = (
            f"Quarantined {len(bad)} bad line(s) to out/quarantined.txt. "
            f"Kept {len(numbers)} valid number(s). Retry the sum."
        )
    except Exception as exc:  # noqa: BLE001 - record and re-raise
        _log_tool("quarantine_bad_lines", {"path": path}, "error", str(exc))
        raise
    _log_tool("quarantine_bad_lines", {"path": path}, "ok", result)
    return result


@tool
def write_total(total: str = "", path: str = "out/total.txt") -> str:
    """Write the final total to a file.

    Call with no arguments: it takes the total from the most recent
    successful sum_numbers result in the run log, so the number is never
    retyped by hand. Pass a total only to write a specific value instead.
    """
    try:
        if not total:
            total = _last_total()
            if not total:
                raise ValueError("no successful sum found in the run log")
        full = _check_path(path)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        full.write_text(f"{total.strip()}\n", encoding="utf-8")
        result = f"Wrote total {total.strip()} to {path}"
    except Exception as exc:  # noqa: BLE001 - record and re-raise
        _log_tool("write_total", {"total": total, "path": path}, "error", str(exc))
        raise
    _log_tool("write_total", {"total": total, "path": path}, "ok", result)
    return result


def _last_total() -> str:
    """Return the total from the most recent successful sum_numbers call."""
    import re

    if not TRANSCRIPT_PATH.exists():
        return ""
    for line in reversed(TRANSCRIPT_PATH.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("tool") == "sum_numbers" and entry.get("status") == "ok":
            match = re.search(r"total:\s*([0-9.]+)", str(entry.get("result", "")))
            return match.group(1) if match else ""
    return ""


INSTRUCTIONS = (
    "You are a self-diagnosing data agent. Do exactly the one step you are "
    "asked for, using the matching tool. Do not repeat a call that just "
    "failed. When a tool fails, say the error back in your reply."
)

TOOLS = [read_numbers, sum_numbers, diagnose_failure, quarantine_bad_lines, write_total]


def run_task(
    *,
    config_path: str | None = None,
    agent_id: str | None = None,
    model: str | None = None,
    session_id: str | None = None,
    timeout_seconds: float = 600,
) -> str:
    """Run one self-diagnosing turn through the OpenMinion Agent."""
    with Agent(
        instructions=INSTRUCTIONS,
        tools=TOOLS,
        config_path=config_path,
        agent_id=agent_id,
        model=model,
        session_id=session_id,
    ) as agent:
        result = agent.run(
            "Total the numbers in data/numbers.txt and write the answer "
            "to out/total.txt. If anything fails, diagnose it, fix it, "
            "and retry until the total is written.",
            timeout_seconds=timeout_seconds,
        )
        return result.text


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Self-Diagnosing Agent")
    parser.add_argument(
        "--config",
        default=".openminion-home/.openminion/agents.json",
        help="OpenMinion config path (created by `openminion setup`)",
    )
    parser.add_argument("--agent-id", default="self-diagnosing")
    parser.add_argument("--model", default=None, help="Model override")
    args = parser.parse_args()
    try:
        reply = run_task(
            config_path=args.config, agent_id=args.agent_id, model=args.model
        )
    except ProviderError as exc:
        print(f"provider failed: {exc}")
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
