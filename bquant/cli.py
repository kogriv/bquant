"""
BQuant CLI Module

Командный интерфейс пакета: ``bquant`` из ``[project.scripts]``.

Про правдивость выхода
======================

Это исполняемый файл, который появляется в ``PATH`` после ``pip install bquant``,
и он же описан в ``README.md`` — витрине PyPI. Поэтому здесь особенно дорого стоит
расхождение между **именем** команды и **смыслом** её выхода.

Раньше ``analyze`` считал MACD, клал результат в переменную, которую никто не читал,
и рисовал график сырых цен: в HTML не было ни одного вхождения «macd», а ось времени
синтезировалась из умолчания (``date_range('2024-01-01', …)``) вместо чтения из данных.
Команда завершалась словами «Анализ завершен успешно!», не назвав ни одного числа,
полученного из данных.

Правило модуля: **команда, названная анализом, обязана вернуть результат анализа**, а
всё, что она печатает или рисует, обязано быть посчитано, а не подставлено по умолчанию.
Пины на это — ``tests/unit/test_cli_says_what_it_does.py``.

Разделение обязанностей здесь тоже про это: :func:`run_zone_analysis` и :func:`summarize`
ничего не печатают и **поднимают исключения**, а не завершают процесс; ``sys.exit``
остаётся только в :func:`main`, потому что решать судьбу процесса вправе точка входа,
а не библиотечная функция, которую кто-то импортировал.
"""

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .core.exceptions import BQuantError, ConfigurationError
from .core.logging_config import get_logger
from .data.samples import get_sample_data, list_datasets, print_sample_data_status
from .visualization import charts

logger = get_logger(__name__)


#: Что умеет считать ``analyze``. Индикатор — **параметр**, а не значение имени
#: команды: пайплайн зон индикатор-агностичен, и зашивать MACD в слово «анализ»
#: значило бы вернуть ту самую слипшуюся идентичность-со-смыслом, которую
#: разводили в G8/G20. Все три пресета доступны из коробки — ``pandas-ta``
#: стоит в основных зависимостях пакета.
SUPPORTED_INDICATORS = ('macd', 'rsi', 'ao')

DEFAULT_DATASET = 'tv_xauusd_1h'


def run_zone_analysis(dataset_name: str = DEFAULT_DATASET,
                      indicator: str = 'macd',
                      min_duration: int = 1,
                      clustering: bool = True):
    """
    Посчитать зоны по выбранному индикатору на встроенном наборе данных.

    Функция **чистая относительно вывода**: ничего не печатает и не завершает
    процесс, а поднимает исключение из иерархии :mod:`bquant.core.exceptions`.

    Args:
        dataset_name: имя встроенного набора (см. :func:`list_datasets`)
        indicator: один из :data:`SUPPORTED_INDICATORS`
        min_duration: порог длительности для агрегатов (зоны короче остаются
            в ``result.zones``, но не входят в статистику; сколько их —
            в ``result.metadata['duration_filter']``)
        clustering: выполнять кластеризацию зон

    Returns:
        ``ZoneAnalysisResult``

    Raises:
        ConfigurationError: индикатор не поддерживается
        BQuantError: анализ не удался
    """
    if indicator not in SUPPORTED_INDICATORS:
        raise ConfigurationError(
            f"Unsupported indicator: {indicator}. "
            f"Supported: {', '.join(SUPPORTED_INDICATORS)}"
        )

    from .analysis.zones import (
        analyze_ao_zones,
        analyze_macd_zones,
        analyze_rsi_zones,
    )

    presets = {
        'macd': analyze_macd_zones,
        'rsi': analyze_rsi_zones,
        'ao': analyze_ao_zones,
    }

    # Время на индекс ставит сам пайплайн (G30) — своего обхода здесь больше нет.
    data = get_sample_data(dataset_name)
    logger.info(f"Loaded {len(data)} rows from sample dataset '{dataset_name}'")

    return presets[indicator](
        data, min_duration=min_duration, clustering=clustering
    )


def _jsonable(value: Any) -> Any:
    """Привести значение к тому, что переживёт ``json.dumps``.

    Статистика приходит с numpy-скалярами (``np.float64``, ``np.bool_``) и
    ``datetime``; без этого шага ``--json`` падал бы на сериализации там, где
    считалось всё правильно.
    """
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (datetime, Path)):
        return str(value)
    if hasattr(value, 'item') and getattr(value, 'shape', None) == ():
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        # NaN и inf — валидный float в Python, но не валидный JSON.
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


#: Версия структуры, которую печатает ``--json``. Потребитель здесь — программа,
#: поэтому у формы должен быть номер, по которому её можно отличить.
SUMMARY_SCHEMA_VERSION = 1


def summarize(result, dataset_name: str = '', indicator: str = '') -> Dict[str, Any]:
    """
    Свести результат анализа к плоской структуре, пригодной и для печати, и для JSON.

    Args:
        result: ``ZoneAnalysisResult``
        dataset_name: имя набора, по которому считали (для протокола)
        indicator: имя индикатора (для протокола)

    Returns:
        Словарь, который переживает ``json.dumps``.
    """
    zones = list(result.zones or [])

    by_type: Dict[str, int] = {}
    for zone in zones:
        by_type[zone.type] = by_type.get(zone.type, 0) + 1

    durations = [zone.duration for zone in zones if zone.duration is not None]

    schema = {}
    if result.column_schema is not None:
        schema = {
            f"{indicator_id}:{role}": column
            for (indicator_id, role), column in result.column_schema.entries.items()
        }

    total_statistics = (result.statistics or {}).get('total_statistics', {})
    duration_filter = (result.metadata or {}).get('duration_filter', {})

    summary = {
        'schema_version': SUMMARY_SCHEMA_VERSION,
        'dataset': dataset_name,
        'indicator': indicator,
        'zones': {
            'total': len(zones),
            'by_type': by_type,
            'duration': {
                'min': min(durations) if durations else None,
                'max': max(durations) if durations else None,
                'mean': (sum(durations) / len(durations)) if durations else None,
            },
        },
        'duration_filter': duration_filter,
        'total_statistics': total_statistics,
        'columns': schema,
        'clustering': (result.clustering or {}).get('clustering_summary'),
    }
    return _jsonable(summary)


def render_summary(summary: Dict[str, Any], brief: bool = False) -> str:
    """Человекочитаемая сводка — из того же словаря, что уходит в ``--json``.

    Один источник на оба вида вывода: иначе текст и JSON расходятся, и по одному
    из них люди делают выводы, которых другой не подтверждает.

    Args:
        summary: сводка из :func:`summarize`
        brief: короткая форма (``--quiet``) — одна строка с результатом.
            Именно **с результатом**: краткость сокращает подробности, а не
            обязанность назвать посчитанное.
    """
    zones = summary.get('zones', {})

    if brief:
        by_type = zones.get('by_type') or {}
        parts = ", ".join(f"{name}: {count}" for name, count in sorted(by_type.items()))
        total = zones.get('total', 0)
        return f"{total} зон" + (f" ({parts})" if parts else "")

    lines = [
        f"Набор данных: {summary.get('dataset')}",
        f"Индикатор:    {summary.get('indicator')}",
        f"Найдено зон:  {zones.get('total', 0)}",
    ]

    by_type = zones.get('by_type') or {}
    if by_type:
        parts = ", ".join(f"{name}: {count}" for name, count in sorted(by_type.items()))
        lines.append(f"  по типам:   {parts}")

    duration = zones.get('duration') or {}
    if duration.get('mean') is not None:
        lines.append(
            f"  длительность (баров): мин {duration['min']}, "
            f"средн {duration['mean']:.1f}, макс {duration['max']}"
        )

    excluded = (summary.get('duration_filter') or {}).get('zones_excluded')
    if excluded:
        lines.append(
            f"  вне агрегатов по порогу длительности: {excluded} "
            f"(остаются в результате)"
        )

    clustering = summary.get('clustering') or {}
    if clustering.get('n_clusters'):
        lines.append(f"Кластеров:    {clustering['n_clusters']}")

    columns = summary.get('columns') or {}
    if columns:
        lines.append("Колонки индикатора:")
        for role, column in sorted(columns.items()):
            lines.append(f"  {role} -> {column}")

    return "\n".join(lines)


def render_chart(result, output_file: Optional[str], dataset_name: str,
                 indicator: str) -> Path:
    """
    Нарисовать зоны поверх посчитанного индикатора и сохранить в HTML.

    Кадр берётся из ``result.data`` — с посчитанным индикатором, — а колонки
    резолвятся по **ролям** через ``result.column_schema``, а не по угаданным
    именам. Раньше сюда уходили сырые цены, и график не показывал ничего из того,
    что было посчитано.

    Returns:
        Путь сохранённого файла.
    """
    if output_file:
        target = Path(output_file)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path("results/charts") / f"zones_{indicator}_{dataset_name}_{timestamp}.html"

    target.parent.mkdir(parents=True, exist_ok=True)

    figure = charts.create_zones_chart(
        result.data,
        zones_data=result.zones,
        title=f"{indicator.upper()} zones — {dataset_name}",
        column_schema=result.column_schema,
    )
    figure.write_html(str(target))
    return target


def analyze_dataset(dataset_name: str = DEFAULT_DATASET,
                    indicator: str = 'macd',
                    output_file: Optional[str] = None,
                    quiet: bool = False,
                    as_json: bool = False,
                    no_chart: bool = False) -> Dict[str, Any]:
    """
    Реализация команды ``analyze``: посчитать зоны, отчитаться, нарисовать.

    Печатает, но **не завершает процесс** — исключения уходят наверх, в :func:`main`.

    Returns:
        Ту же сводку, что печатается (удобно для тестов и для встраивания).
    """
    if not (quiet or as_json):
        print(f"🔍 Анализ зон ({indicator.upper()}) для датасета: {dataset_name}")

    result = run_zone_analysis(dataset_name, indicator=indicator)
    summary = summarize(result, dataset_name=dataset_name, indicator=indicator)

    chart_path = None
    if not no_chart:
        chart_path = render_chart(result, output_file, dataset_name, indicator)
        summary['chart'] = str(chart_path)

    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary

    # `--quiet` укорачивает отчёт, но не отменяет его: команда всё равно обязана
    # назвать результат. Молчаливое «готово» — это отчёт о том, что код не упал,
    # а не о том, что что-то посчитано.
    print(render_summary(summary, brief=quiet))
    if chart_path is not None:
        print(f"График: {chart_path}")

    return summary


def list_available_data() -> None:
    """Показать список доступных sample данных."""
    print("📋 Доступные sample данные:")
    print("=" * 50)

    datasets = list_datasets()
    for i, dataset in enumerate(datasets, 1):
        print(f"{i}. {dataset['title']} ({dataset['name']})")
        print(f"   Символ: {dataset['symbol']} | Таймфрейм: {dataset['timeframe']}")
        print(f"   Записей: {dataset['rows']:,} | Размер: {dataset['size_kb']} KB")
        print()

    print(f"Всего доступно датасетов: {len(datasets)}")


def show_data_status() -> None:
    """Показать статус всех sample данных."""
    print_sample_data_status()


def build_parser() -> argparse.ArgumentParser:
    """Собрать разбор аргументов (вынесен, чтобы его можно было проверить)."""

    parser = argparse.ArgumentParser(
        prog="bquant",
        description="BQuant - Quantitative Research Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  bquant analyze                       # Зоны по MACD на данных по умолчанию
  bquant analyze mt_xauusd_m15         # Зоны на конкретном датасете
  bquant analyze --indicator rsi       # Зоны по RSI (пороговая детекция)
  bquant analyze --json                # Структурный вывод для программ
  bquant analyze --json --no-chart     # Только числа, без отрисовки
  bquant analyze --output chart.html   # Сохранение графика в файл
  bquant list                          # Список доступных данных
  bquant status                        # Статус всех данных
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')

    analyze_parser = subparsers.add_parser(
        'analyze', help='Анализ зон по выбранному индикатору'
    )
    analyze_parser.add_argument(
        'dataset',
        nargs='?',
        default=DEFAULT_DATASET,
        help=f'Название датасета (по умолчанию: {DEFAULT_DATASET})'
    )
    analyze_parser.add_argument(
        '--indicator', '-i',
        choices=SUPPORTED_INDICATORS,
        default='macd',
        help='Индикатор, по которому детектируются зоны (по умолчанию: macd)'
    )
    analyze_parser.add_argument(
        '--output', '-o',
        help='Путь для сохранения графика (HTML файл)'
    )
    analyze_parser.add_argument(
        '--json',
        dest='as_json',
        action='store_true',
        help='Структурный вывод (JSON) вместо текстового отчёта'
    )
    analyze_parser.add_argument(
        '--no-chart',
        action='store_true',
        help='Не строить график (только расчёт)'
    )
    analyze_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Минимальный вывод (без подробной информации)'
    )

    subparsers.add_parser('list', help='Список доступных данных')
    subparsers.add_parser('status', help='Статус всех данных')

    return parser


def main() -> None:
    """Точка входа CLI — единственное место, которое вправе завершить процесс."""

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'analyze':
            analyze_dataset(
                args.dataset,
                indicator=args.indicator,
                output_file=args.output,
                quiet=args.quiet,
                as_json=args.as_json,
                no_chart=args.no_chart,
            )
        elif args.command == 'list':
            list_available_data()
        elif args.command == 'status':
            show_data_status()

    except KeyboardInterrupt:
        print("\n⚠️ Операция прервана пользователем", file=sys.stderr)
        sys.exit(130)
    except BQuantError as e:
        # Ошибка, которую пакет умеет назвать: печатаем её, а не трассировку.
        print(f"❌ {type(e).__name__}: {e}", file=sys.stderr)
        logger.error(f"{args.command} failed: {e}")
        sys.exit(1)
    except Exception as e:
        # Всё остальное — не наша предметная ошибка. Раньше и она сводилась
        # к строчке текста, и причина терялась вместе с трассировкой.
        logger.exception(f"Unexpected error in CLI command '{args.command}'")
        print(f"❌ Неожиданная ошибка: {type(e).__name__}: {e}", file=sys.stderr)
        raise


if __name__ == '__main__':
    main()
