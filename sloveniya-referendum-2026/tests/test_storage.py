"""Тесты хранилища: снимки только изменений и дедупликация трендов."""

from sloref.models import Aggregates
from sloref.storage import TIMESERIES_COLUMNS, Store


def make_store(tmp_path):
    return Store(tmp_path / "data")


def test_save_file_snapshots_only_changes(tmp_path):
    store = make_store(tmp_path)
    assert store.save_file("ref", "rezultati.json", b"v1", "2026-10-11_2000") is True
    # то же содержимое — снимок не создаётся, latest обновляется
    assert store.save_file("ref", "rezultati.json", b"v1", "2026-10-11_2015") is False
    # новое содержимое — новый снимок
    assert store.save_file("ref", "rezultati.json", b"v2", "2026-10-11_2030") is True

    # по снимку на каждое изменение: v1 (2000) и v2 (2030)
    snapshots = sorted(p.name for p in (store.raw).glob("*/*/*/*"))
    assert snapshots == ["rezultati.json", "rezultati.json"]
    snap_dirs = sorted(p.name for p in (store.raw / "2026-10-11").iterdir())
    assert snap_dirs == ["2000", "2030"]
    assert (store.latest / "ref" / "rezultati.json").read_bytes() == b"v2"


def test_timeseries_dedup_and_append(tmp_path):
    store = make_store(tmp_path)
    poll = "2026-10-11T20:00:00+00:00"

    agg1 = Aggregates(referendum="ref", source_datum="d1", za=100, za_pct=0.4,
                      proti=150, proti_pct=0.6)
    assert store.append_timeseries(agg1, poll) is True
    # без изменений строка не добавляется
    assert store.append_timeseries(agg1, poll) is False
    # изменившиеся цифры добавляют строку
    agg2 = Aggregates(referendum="ref", source_datum="d2", za=110, za_pct=0.42,
                      proti=152, proti_pct=0.58)
    assert store.append_timeseries(agg2, poll) is True

    lines = store.timeseries.read_text(encoding="utf-8").strip().split("\n")
    assert lines[0].split(";") == TIMESERIES_COLUMNS
    assert len(lines) == 3
    assert ";d1;" in lines[1] and ";d2;" in lines[2]


def test_state_survives_reopen(tmp_path):
    """Сигнатура хранится на диске: новый Store не дублирует точку тренда."""
    store = make_store(tmp_path)
    agg = Aggregates(referendum="ref", source_datum="d1", za=1)
    assert store.append_timeseries(agg, "t1") is True
    assert make_store(tmp_path).append_timeseries(agg, "t2") is False
