"""Demo runner: resets the input, drives the agent one step at a time,
verifies the result, and saves a transcript.

Why one step at a time, one tool at a time: the demo model is
qwen2.5:0.5b, a tiny local model. In a single run it could not hold the
five-step fail-diagnose-fix-retry plan: it repeated the failing sum call
until the runtime's loop guard stopped it, and never called diagnose.
Given one narrow instruction per turn it makes the right call, but it also
repeats the call instead of stopping, so each turn exposes exactly ONE
tool: the model can only call that tool, then it must answer in text.
The model still chooses the call and its arguments within each turn; the
runner only sequences the steps and checks each one landed. This is
stated plainly in the README.

Expected total: 12 + 7 + 23 + 41 + 5 + 18 = 106.
The bad line is 'twelve' on line 4.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "numbers.txt"
OUT_DIR = BASE_DIR / "out"
RUNS_DIR = BASE_DIR / "runs"
TRANSCRIPT_JSONL = BASE_DIR / "runs" / "latest" / "tool_calls.jsonl"

EXPECTED_TOTAL = "106"

ORIGINAL_DATA = "12\n7\n23\ntwelve\n41\n5\n18\n"

TURN_TIMEOUT = 180


class StepFailed(Exception):
    pass


def reset() -> None:
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    (BASE_DIR / "runs" / "latest").mkdir(parents=True, exist_ok=True)
    if TRANSCRIPT_JSONL.exists():
        TRANSCRIPT_JSONL.unlink()
    DATA_FILE.write_text(ORIGINAL_DATA, encoding="utf-8")


def read_entries() -> list[dict]:
    if not TRANSCRIPT_JSONL.exists():
        return []
    return [
        json.loads(line)
        for line in TRANSCRIPT_JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def make_agent(tools, *, config, agent_id, model, session_id):
    from openminion import Agent

    from self_diagnosing_agent.agent import INSTRUCTIONS

    return Agent(
        instructions=INSTRUCTIONS,
        tools=tools,
        config_path=config,
        agent_id=agent_id,
        model=model,
        session_id=session_id,
    )


def run_step(*, tools, prompt, expect_tool, expect_status,
             config, agent_id, model, session_id) -> list[dict]:
    """Run one turn with exactly one tool available; check it ran as expected.

    Retries once with a blunter prompt. Returns the new transcript entries.
    """
    before = len(read_entries())
    # Prompts start with "tool <name>": OpenMinion skips its LLM freshness
    # classifier for explicit tool requests. Without this, the tiny local
    # model sometimes misclassifies a local file task as a time-sensitive
    # finance request and the runtime refuses with a "grounded current
    # finance answer" template instead of calling the tool.
    attempts = [
        f"tool {expect_tool} {prompt} After the tool result, reply in one short sentence and stop.",
        f"tool {expect_tool} {prompt} Use only the {expect_tool} tool, then stop.",
    ]
    last_error = ""
    for i, attempt in enumerate(attempts):
        print(f"\n--- step: {prompt} (attempt {i + 1}) ---")
        with make_agent(tools, config=config, agent_id=agent_id,
                        model=model, session_id=session_id) as agent:
            reply = agent.run(attempt, timeout_seconds=TURN_TIMEOUT)
        print(f"agent: {reply.text[:300]}")
        new_entries = read_entries()[before:]
        matching = [
            e for e in new_entries
            if e["tool"] == expect_tool and e["status"] == expect_status
        ]
        if matching:
            return new_entries
        errs = [e for e in new_entries if e["status"] == "error"]
        if errs:
            last_error = errs[-1]["result"]
        print(
            f"  !! expected {expect_tool} [{expect_status}] did not happen; "
            f"got: {[(e['tool'], e['status']) for e in new_entries] or 'no tool calls'}"
        )
    raise StepFailed(
        f"step failed: {expect_tool} [{expect_status}] never happened. "
        f"Last error seen: {last_error or 'none'}"
    )


def verify() -> bool:
    total_file = OUT_DIR / "total.txt"
    if not total_file.exists():
        print("VERIFY FAIL: out/total.txt was not written.")
        return False
    actual = total_file.read_text(encoding="utf-8").strip()
    if actual in (EXPECTED_TOTAL, "106.0"):
        print(f"VERIFY PASS: out/total.txt = {actual} (expected {EXPECTED_TOTAL}).")
        return True
    print(f"VERIFY FAIL: out/total.txt = {actual!r}, expected {EXPECTED_TOTAL}.")
    return False


def save_transcript(run_dir: Path, final_reply: str, passed: bool) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    entries = read_entries()
    md = [
        "# Self-Diagnosing Agent — demo transcript",
        "",
        f"Run: {time.strftime('%Y-%m-%d %H:%M:%S')} (local time)",
        "Model: local Ollama qwen2.5:0.5b via OpenMinion 0.1",
        "Input: data/numbers.txt (bad line: 'twelve' on line 4)",
        f"Expected total: {EXPECTED_TOTAL}",
        f"Verification: {'PASS' if passed else 'FAIL'}",
        "",
        "## Tool calls (real executions, in order)",
        "",
    ]
    if not entries:
        md.append("(no tool calls were recorded)")
    for e in entries:
        md.append(
            f"- {e['time']} `{e['tool']}` [{e['status']}] "
            f"args={json.dumps(e['args'])}\n  result: {e['result']}"
        )
    md += ["", "## Agent final summary", "", final_reply, ""]
    (run_dir / "transcript.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Transcript saved to {run_dir / 'transcript.md'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=".openminion-home/.openminion/agents.json",
        help="OpenMinion config path (created by `openminion setup`)",
    )
    parser.add_argument("--agent-id", default="self-diagnosing")
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--session-id",
        default=None,
        help="Session id (default: fresh self-diagnosing-<timestamp>)",
    )
    args = parser.parse_args()

    reset()
    session_id = args.session_id or (
        "self-diagnosing-" + time.strftime("%Y%m%d-%H%M%S")
    )
    print("=== Self-Diagnosing Agent demo ===")
    print("Input data/numbers.txt has a bad line: 'twelve' on line 4.")
    print("The agent must fail, diagnose, fix, retry, and write the total.")
    print(f"Session: {session_id}")

    from self_diagnosing_agent.agent import (
        diagnose_failure,
        quarantine_bad_lines,
        read_numbers,
        sum_numbers,
        write_total,
    )

    common = dict(config=args.config, agent_id=args.agent_id,
                  model=args.model, session_id=session_id)
    final_reply = ""
    try:
        run_step(tools=[read_numbers],
                 prompt="Call read_numbers for data/numbers.txt.",
                 expect_tool="read_numbers", expect_status="ok", **common)
        entries = run_step(
            tools=[sum_numbers],
            prompt="Call sum_numbers for data/numbers.txt.",
            expect_tool="sum_numbers", expect_status="error", **common)
        run_step(
            tools=[diagnose_failure],
            prompt="The sum failed. Call diagnose_failure with no arguments. "
                   "It reads the last failure from the run log and explains it.",
            expect_tool="diagnose_failure", expect_status="ok", **common)
        run_step(
            tools=[quarantine_bad_lines],
            prompt="Follow the diagnosis. Call quarantine_bad_lines for "
                   "data/numbers.txt.",
            expect_tool="quarantine_bad_lines", expect_status="ok", **common)
        entries = run_step(
            tools=[sum_numbers],
            prompt="Call sum_numbers for data/numbers.txt again.",
            expect_tool="sum_numbers", expect_status="ok", **common)
        run_step(
            tools=[write_total],
            prompt="Call write_total with no arguments. It takes the total "
                   "from the last successful sum in the run log and writes "
                   "it to out/total.txt.",
            expect_tool="write_total", expect_status="ok", **common)
        with make_agent([], **common) as agent:
            final = agent.run(
                "Summarise from the tool results already in this conversation: "
                "what failed, why, what you fixed, and the final total. "
                "No live data is needed; everything is in the conversation history.",
                timeout_seconds=TURN_TIMEOUT,
            )
            final_reply = final.text
    except Exception as exc:  # noqa: BLE001 - demo must report, not crash
        print(f"\nDEMO FAILED: {exc!r}")
        save_transcript(RUNS_DIR / time.strftime("%Y%m%d-%H%M%S"), "", False)
        return 1

    print()
    print("--- agent summary ---")
    print(final_reply)
    print("---------------------")
    passed = verify()
    save_transcript(RUNS_DIR / time.strftime("%Y%m%d-%H%M%S"), final_reply, passed)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
