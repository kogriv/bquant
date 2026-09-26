"""G86: откат `save_figure` с PNG на HTML называет причину.

`except Exception` вокруг `write_image` выбрасывал исключение и возвращал путь к
`.html`. Откат задокументирован и остаётся; теряться перестаёт причина — «нет Chrome»,
«несовместимый kaleido» (G85) и любая другая снаружи были неотличимы.

Запись: `devref/gaps/visualization/g86_save_figure_fell_back_to_html_without_a_word_2026-09.md`.
"""

import logging

import pytest

go = pytest.importorskip("plotly.graph_objects")

from bquant.visualization import export  # noqa: E402

REASON = "probe: the image engine is not here"


@pytest.fixture
def export_log(caplog):
    # Логгеры пакета настроены с `propagate=False`: `caplog` вешается на сам логгер.
    export.logger.addHandler(caplog.handler)
    previous = export.logger.level
    export.logger.setLevel(logging.WARNING)
    try:
        yield caplog
    finally:
        export.logger.removeHandler(caplog.handler)
        export.logger.setLevel(previous)


@pytest.fixture
def failing_png(monkeypatch):
    def refuse(self, *args, **kwargs):
        raise RuntimeError(REASON)

    monkeypatch.setattr(go.Figure, "write_image", refuse)


def _figure():
    return go.Figure(go.Scatter(y=[1, 2, 3]))


def test_the_fallback_still_saves_html(tmp_path, failing_png, export_log):
    path = export.save_figure(_figure(), "probe", output_dir=str(tmp_path), prefer="png")
    assert path.endswith(".html")
    assert (tmp_path / "probe.html").exists()


def test_the_fallback_names_the_reason(tmp_path, failing_png, export_log):
    export.save_figure(_figure(), "probe", output_dir=str(tmp_path), prefer="png")
    warnings = [r.getMessage() for r in export_log.records if r.levelno == logging.WARNING]
    assert any(REASON in m and "probe" in m for m in warnings), (
        f"PNG fell back to HTML without saying why; warnings: {warnings}"
    )


def test_html_asked_for_is_not_a_fallback(tmp_path, failing_png, export_log):
    """Положительный контроль: HTML по просьбе — не откат, и предупреждать не о чем."""
    path = export.save_figure(_figure(), "probe", output_dir=str(tmp_path), prefer="html")
    assert path.endswith(".html")
    assert not [r for r in export_log.records if r.levelno >= logging.WARNING]
