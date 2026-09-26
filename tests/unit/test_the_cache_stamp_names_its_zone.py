"""G83: отметка времени в записи кэша зон называет свой часовой пояс.

`created_at` писался через `datetime.utcnow()` — UTC без пояса, строка неотличима от
местного времени, которым пишут остальные отметки пакета. Проверяется **свойство**
(пояс есть и он UTC), а не отсутствие `DeprecationWarning`: предупреждение можно
заглушить фильтром, пустой пояс — нет.

Запись: `devref/gaps/cache/g83_the_cache_stamp_was_utc_and_did_not_say_so_2026-09.md`.
"""

from datetime import datetime, timedelta, timezone

from bquant.analysis.zones.cache import ZoneAnalysisCache


class _RecordingManager:
    def __init__(self):
        self.payloads = []

    def put(self, key, payload, **kwargs):
        self.payloads.append(payload)


def _saved_stamp() -> datetime:
    manager = _RecordingManager()
    ZoneAnalysisCache(manager).save("key", result=object())
    assert len(manager.payloads) == 1, "save() did not reach the cache manager"
    return datetime.fromisoformat(manager.payloads[0]["metadata"]["created_at"])


def test_the_stamp_carries_a_zone():
    stamp = _saved_stamp()
    assert stamp.tzinfo is not None, f"created_at has no zone: {stamp.isoformat()}"
    assert stamp.utcoffset() == timedelta(0)


def test_the_stamp_is_the_moment_of_saving():
    """Пояс не должен быть приклеен к чужому времени: момент тот же, что сейчас по UTC."""
    before = datetime.now(timezone.utc)
    stamp = _saved_stamp()
    after = datetime.now(timezone.utc)
    assert before <= stamp <= after
