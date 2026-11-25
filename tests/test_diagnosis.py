"""Unit tests for the diagnosis logic. No model or network needed."""

from pathlib import Path

from self_diagnosing_agent.diagnosis import diagnose, parse_numbers

SAMPLE = "12\n7\n23\ntwelve\n41\n5\n18\n"


def test_parse_numbers_splits_good_and_bad(tmp_path: Path) -> None:
    f = tmp_path / "n.txt"
    f.write_text(SAMPLE, encoding="utf-8")
    numbers, bad = parse_numbers(f)
    assert numbers == [12.0, 7.0, 23.0, 41.0, 5.0, 18.0]
    assert sum(numbers) == 106.0
    assert len(bad) == 1
    assert bad[0].line_number == 4
    assert bad[0].text == "twelve"


def test_diagnose_bad_lines_names_the_cause(tmp_path: Path) -> None:
    f = tmp_path / "n.txt"
    f.write_text(SAMPLE, encoding="utf-8")
    d = diagnose(f)
    assert d.kind == "bad_lines"
    assert "twelve" in d.cause
    assert "line 4" in d.cause.lower()
    assert "quarantine_bad_lines" in d.recommended_fix
    assert d.valid_count == 6


def test_diagnose_missing_file(tmp_path: Path) -> None:
    d = diagnose(tmp_path / "nope.txt")
    assert d.kind == "missing_file"


def test_diagnose_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "n.txt"
    f.write_text("\n", encoding="utf-8")
    assert diagnose(f).kind == "empty_file"


def test_diagnose_clean_file(tmp_path: Path) -> None:
    f = tmp_path / "n.txt"
    f.write_text("1\n2\n3\n", encoding="utf-8")
    assert diagnose(f).kind == "ok"
