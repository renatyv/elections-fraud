"""Тесты извлечения показателей из JSON DVK."""

from pathlib import Path

from sloref.models import extract_aggregates

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_full_extraction():
    agg = extract_aggregates("preiskava",
                             load("rezultati_sample.json"),
                             load("udelezba_sample.json"))
    assert agg.source_datum == "2026-10-11T20:35:00Z"
    assert agg.turnout_case == "19:00"
    assert agg.electorate == 1711779
    assert agg.voters == 825965
    assert agg.turnout_pct == 0.4825
    assert agg.ballots == 825838
    assert agg.valid == 814995
    assert agg.invalid == 10843
    assert agg.za == 325406 and agg.za_pct == 0.3993
    assert agg.proti == 489589 and agg.proti_pct == 0.6007
    # доля посчитанных бюллетеней = посчитано / голосовавших
    assert agg.counted_pct == 825838 / 825965


def test_empty_files_contain_only_datum():
    """До публикации данных в файле есть только поле «datum»."""
    agg = extract_aggregates("rtv_prispevek",
                             load("rezultati_empty.json"),
                             load("rezultati_empty.json"))
    assert agg.source_datum == "2026-10-02T09:00:00Z"
    assert agg.za is None and agg.proti is None
    assert agg.turnout_pct is None
    assert agg.counted_pct is None


def test_missing_files():
    agg = extract_aggregates("x", None, None)
    assert agg.source_datum is None
    assert agg.signature().startswith("{")


def test_signature_stable():
    a1 = extract_aggregates("x", load("rezultati_sample.json"), None)
    a2 = extract_aggregates("x", load("rezultati_sample.json"), None)
    assert a1.signature() == a2.signature()
    a3 = extract_aggregates("x", load("rezultati_sample.json"),
                            load("udelezba_sample.json"))
    assert a1.signature() != a3.signature()
