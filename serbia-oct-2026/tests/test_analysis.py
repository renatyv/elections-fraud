"""Regression checks for Serbia's source adaptation and electoral rules."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_ef_csv as adapter
import analyze_paradoxes as paradoxes


def test_turnout_includes_invalid_and_unaccounted_ballots() -> None:
    unit = adapter.Unit("RS-1", "region", "unit", 1000, 600, 650, 40, {1: 600})
    rows, _ = adapter.mai_rows([unit], 680072, 2026)
    assert rows[0]["voted"] == 650
    assert rows[0]["turnout_pct"] == 65
    assert rows[0]["null_votes"] == 40


def test_special_registers_use_latest_snapshot(monkeypatch, tmp_path: Path) -> None:
    for stamp, count in [("20261026_140000", 10), ("20261026_160000", 20)]:
        folder = tmp_path / "raw" / "680072" / stamp
        folder.mkdir(parents=True)
        (folder / "region_100.json").write_text(json.dumps({
            "table_data": [{"count_number": 1, "won_number": str(count)}]}))
    monkeypatch.setattr(adapter, "DATA", tmp_path)
    assert adapter._special_votes(680072) == {1: 20}


def test_minority_bonus_changes_seats() -> None:
    votes = {1: 600, 3: 350, 5: 20}
    assert paradoxes.dhondt(votes, 50)[5] == 1
    result = paradoxes.legal_dhondt(votes, voters=1000, seats=50)
    assert result[5] == 1
    assert sum(result.values()) == 50
    # At two seats, the boost overtakes the large list's second quotient.
    assert paradoxes.dhondt({1: 100, 5: 40}, 2) == {1: 2, 5: 0}
    assert paradoxes.legal_dhondt({1: 100, 5: 40}, voters=2000, seats=2) == {1: 1, 5: 1}


def test_threshold_uses_voters_who_voted() -> None:
    result = paradoxes.legal_dhondt({1: 9700, 2: 300}, voters=11000)
    assert 2 not in result
    assert sum(result.values()) == 250
