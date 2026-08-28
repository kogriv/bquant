"""Пины на след, который пакет оставляет в файловой системе (G24).

Почему этот файл нельзя было написать раньше
============================================

Сьют гоняется по рабочей копии, где ``PROJECT_ROOT`` — «три уровня вверх от
``bquant/core/config.py``» — попадает точно в корень репозитория. Там всё верно, и
дефект не виден **ровно тому, кто его правит**. У установленного пакета те же три
уровня вверх дают `site-packages`, и пакет начинает создавать каталоги и писать логи
внутрь собственной установки; при отсутствии права записи — падает прямо на импорте.

Замер на чистом окружении, `pip install bquant==0.0.7`::

    $ chmod -w site-packages
    $ python -c "import bquant"
    PermissionError: [Errno 13] Permission denied: '…/site-packages/logs'

Поэтому проверки здесь устроены так, чтобы **не зависеть от того, что мы сейчас в
чекауте**: они либо подставляют корень, не похожий на чекаут, либо смотрят на импорт
из отдельного процесса. Разбор: ``devref/gaps/install/g24_*.md``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from bquant.core import config


# --- Импорт не должен ничего создавать -------------------------------------


def test_importing_bquant_creates_no_directories():
    """``import bquant`` не имеет права создавать каталоги.

    Создание на импорте — это не «удобная подготовка», а перенос отказа прав в
    точку, где вызывающий ничего не может сделать: он ещё не попросил ничего
    записать, а импорт уже упал. Всё, что действительно пишет, создаёт каталог
    само (``core/utils.py``, ``core/logging_config.py``, ``core/cache.py``).

    Проверка — в отдельном процессе, потому что в текущем пакет уже импортирован.
    """

    probe = (
        "import pathlib, sys\n"
        "created = []\n"
        "def refuse(self, *args, **kwargs):\n"
        "    created.append(str(self))\n"
        "    raise AssertionError('import created a directory: %s' % self)\n"
        "pathlib.Path.mkdir = refuse\n"
        "import bquant\n"
        "print('NO-DIRS-CREATED')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True, text=True, timeout=300,
    )
    assert "NO-DIRS-CREATED" in result.stdout, (
        "импорт пакета создал каталог:\n" + (result.stderr or result.stdout)
    )


# --- Корень для записи отделён от каталога установки ------------------------


def test_a_root_that_is_not_a_checkout_is_not_written_into(tmp_path):
    """Каталог, не похожий на рабочую копию, — это каталог установки.

    Писать туда нельзя: у пользователя он может быть только для чтения, и он не
    его. Функция обязана увести запись в пользовательский каталог.
    """

    fake_install = tmp_path / "site-packages"
    fake_install.mkdir()
    (fake_install / "bquant").mkdir()  # пакет есть, а признаков чекаута нет

    state_root = config.resolve_state_root(fake_install)

    assert not str(state_root).startswith(str(fake_install)), (
        f"состояние пишется внутрь установки: {state_root}"
    )


def test_a_source_checkout_keeps_writing_into_the_repo():
    """В рабочей копии поведение разработчика не меняется.

    Это половина смысла правки: примеры и скрипты продолжают складывать
    результаты в репозиторий, как складывали.
    """

    assert config.is_source_checkout(config.PROJECT_ROOT), (
        "корень репозитория перестал опознаваться как рабочая копия"
    )
    assert config.resolve_state_root(config.PROJECT_ROOT) == config.PROJECT_ROOT


def test_a_checkout_is_recognised_by_the_marks_of_a_checkout(tmp_path):
    """Опознание — по признакам, а не по «наверное, это репозиторий»."""

    root = tmp_path / "repo"
    (root / "bquant").mkdir(parents=True)
    assert not config.is_source_checkout(root), "нет pyproject.toml — не чекаут"

    (root / "pyproject.toml").write_text("[project]\nname='bquant'\n", encoding="utf-8")
    assert config.is_source_checkout(root), "есть и пакет, и pyproject.toml — чекаут"


def test_bquant_home_wins_over_the_default(tmp_path, monkeypatch):
    """У пользователя должен быть способ назвать каталог самому."""

    chosen = tmp_path / "somewhere"
    monkeypatch.setenv("BQUANT_HOME", str(chosen))

    fake_install = tmp_path / "site-packages"
    (fake_install / "bquant").mkdir(parents=True)

    assert config.resolve_state_root(fake_install) == chosen


# --- Пути по умолчанию ------------------------------------------------------


def test_the_default_log_file_lives_under_the_state_root():
    """Лог пишется туда, куда пакету можно писать, а не рядом с его кодом."""

    log_file = Path(config.LOGGING["log_file"])
    assert str(log_file).startswith(str(config.STATE_ROOT)), (
        f"лог по умолчанию {log_file} лежит вне корня состояния {config.STATE_ROOT}"
    )


def test_an_unwritable_log_location_does_not_break_the_package(tmp_path):
    """Некуда писать лог — отваливается лог, а не пакет.

    Второй эшелон к предыдущей проверке: даже если каталог состояния оказался
    недоступен на запись (контейнер без домашнего каталога, урезанные права),
    импорт и работа обязаны продолжиться. Логгирование — служба, а не условие
    существования.
    """

    blocked = tmp_path / "read-only"
    blocked.mkdir()
    blocked.chmod(0o500)
    try:
        probe = (
            "import logging, sys\n"
            "from bquant.core.logging_config import setup_logging, get_logger\n"
            "setup_logging(log_to_file=True, log_file=sys.argv[1], reset_loggers=True)\n"
            "get_logger('bquant.probe').warning('запись, которой некуда лечь')\n"
            "print('SURVIVED')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe, str(blocked / "logs" / "bquant.log")],
            capture_output=True, text=True, timeout=300,
        )
        assert "SURVIVED" in result.stdout, (
            "недоступный для записи лог уронил процесс:\n"
            + (result.stderr or result.stdout)
        )
    finally:
        blocked.chmod(0o700)


@pytest.mark.parametrize("name", ["RESULTS_DIR", "PROCESSED_DATA_DIR", "DATA_DIR"])
def test_writable_defaults_hang_off_the_state_root(name):
    """Все записываемые по умолчанию каталоги — от одного корня.

    Иначе развести «откуда читать код» и «куда писать» получится наполовину, а
    наполовину разведённое различие хуже неразведённого: часть путей уедет, часть
    останется, и объяснить пользователю, какие именно, будет нечем.
    """

    value = Path(getattr(config, name))
    assert str(value).startswith(str(config.STATE_ROOT)), (
        f"{name} = {value} не лежит под STATE_ROOT = {config.STATE_ROOT}"
    )
