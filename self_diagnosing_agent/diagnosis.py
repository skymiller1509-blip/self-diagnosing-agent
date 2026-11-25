"""Pure diagnosis logic for the Self-Diagnosing Agent.

Kept free of OpenMinion imports so it can be unit-tested without a model.
The agent exposes this through the `diagnose_failure` tool.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class BadLine:
    line_number: int
    text: str


@dataclass
class Diagnosis:
    kind: str  # "bad_lines" | "missing_file" | "empty_file" | "all_bad" | "ok"
    cause: str
    bad_lines: list[BadLine]
    valid_count: int
    recommended_fix: str


def parse_numbers(path: Path) -> tuple[list[float], list[BadLine]]:
    """Split a file into valid numbers and bad lines (1-based line numbers)."""
    numbers: list[float] = []
    bad: list[BadLine] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = raw.strip()
        if not text:
            continue
        try:
            numbers.append(float(text))
        except ValueError:
            bad.append(BadLine(line_number=i, text=text))
    return numbers, bad


def diagnose(path: Path) -> Diagnosis:
    """Inspect a numbers file and explain, in plain language, why summing failed."""
    if not path.exists():
        return Diagnosis(
            kind="missing_file",
            cause=f"The file {path} does not exist, so there is nothing to add.",
            bad_lines=[],
            valid_count=0,
            recommended_fix="Create the file with one number per line, then retry.",
        )
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return Diagnosis(
            kind="empty_file",
            cause=f"The file {path} is empty, so the total is undefined.",
            bad_lines=[],
            valid_count=0,
            recommended_fix="Add one number per line, then retry.",
        )
    numbers, bad = parse_numbers(path)
    if not bad:
        return Diagnosis(
            kind="ok",
            cause="Every line is a valid number. Nothing failed.",
            bad_lines=[],
            valid_count=len(numbers),
            recommended_fix="No fix needed. Sum the numbers.",
        )
    if not numbers:
        return Diagnosis(
            kind="all_bad",
            cause=(
                f"Every line in {path} is bad ({len(bad)} bad lines, 0 valid "
                "numbers), so no total can be computed."
            ),
            bad_lines=bad,
            valid_count=0,
            recommended_fix=(
                "Replace the lines with real numbers, then retry. "
                "Quarantining would leave nothing to add."
            ),
        )
    first = bad[0]
    cause = (
        f"Line {first.line_number} says '{first.text}', which is a word, "
        f"not a number. The sum stopped there. {len(bad)} bad line(s) in "
        f"total, {len(numbers)} valid number(s)."
    )
    return Diagnosis(
        kind="bad_lines",
        cause=cause,
        bad_lines=bad,
        valid_count=len(numbers),
        recommended_fix=(
            "Call quarantine_bad_lines: move the bad lines to "
            "out/quarantined.txt, keep the valid numbers, then retry the sum."
        ),
    )


def diagnosis_to_text(d: Diagnosis) -> str:
    """Render a diagnosis as plain text the model can act on."""
    out = [f"cause: {d.cause}", f"recommended fix: {d.recommended_fix}"]
    if d.bad_lines:
        lines = ", ".join(
            f"line {b.line_number} ('{b.text}')" for b in d.bad_lines
        )
        out.append(f"bad lines: {lines}")
    return "\n".join(out)


def diagnosis_to_json(d: Diagnosis) -> str:
    return json.dumps(asdict(d), indent=2)
