"""Декоратор мониторинга работает в обеих формах записи.

G43. `@performance_monitor` без скобок **молча ломал функцию**: фабрика декораторов
получала саму функцию вместо флага `enable_cpu`, декорированное имя становилось
внутренним `decorator`, и вызов возвращал `wrapper` вместо результата. Ни исключения,
ни предупреждения — возвращался объект, у которого правильный вид.

Форма без скобок при этом стояла в `AGENTS.md` — в инструкции проекта, разделом
«Performance Monitoring», как рекомендуемый образец. То есть документированный образец
превращал любую функцию, к которой его применили, в возврат постороннего объекта.
"""

from __future__ import annotations

import pytest

from bquant.core.performance import get_performance_monitor, performance_monitor


@performance_monitor
def bare(values):
    return sum(values)


@performance_monitor()
def called(values):
    return sum(values)


@performance_monitor(enable_cpu=False, enable_memory=False)
def configured(values):
    return sum(values)


@pytest.mark.parametrize("func", [bare, called, configured])
def test_the_decorated_function_returns_its_own_result(func):
    """Главное утверждение: результат — число, а не внутренний объект декоратора."""

    assert func([1, 2, 3]) == 6


@pytest.mark.parametrize("func,name", [(bare, "bare"), (called, "called"),
                                       (configured, "configured")])
def test_the_identity_of_the_function_survives(func, name):
    assert func.__name__ == name


def test_the_call_is_recorded_by_the_monitor():
    """Смысл декоратора — запись метрик; без неё обе формы бесполезны одинаково."""

    monitor = get_performance_monitor()
    monitor.clear_stats()

    bare([1, 2, 3])
    called([1, 2, 3])

    stats = monitor.get_stats()
    recorded = " ".join(stats.keys()) if isinstance(stats, dict) else str(stats)
    assert "bare" in recorded
    assert "called" in recorded


def test_a_positional_flag_is_refused_by_name():
    """`performance_monitor(True)` — не запись без скобок, а ошибка; она должна быть слышной."""

    with pytest.raises(TypeError, match="must be the decorated function"):
        performance_monitor(True)
