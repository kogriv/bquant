# Change Trace Log — 2026-07-20

[17:24:00] [included] [Changed] Бамп версии пакета 0.0.1 → 0.0.2 в pyproject.toml (release под handoff из лабы bquearch)
[17:24:30] [included] [Changed] Бамп __version__ 0.0.1 → 0.0.2 в bquant/__init__.py (версия хардкодится в двух местах)
[17:25:00] [included] [Added] CHANGELOG.md: секция [0.0.2] - 2026-07-20 — Added SwingPoint.confirmation_index (causal availability, PR #107); Changed CACHE_SCHEMA_VERSION → 2
[17:25:30] [included] [Technical] CHANGELOG.md: залежавшийся [Unreleased] переименован в [0.0.1] - 2026-01-12 (фактическое содержимое релиза 0.0.1, собранного в январе)
[17:26:00] [included] [Technical] Прогон pytest: 730 passed, 12 skipped, 3 failed (3 фейла = известный гэп G7 в test_pandas_ta_dynamic_loader.py, пре-существующий, не блокирует)
[17:29:00] [included] [Technical] Чистая сборка dist/bquant-0.0.2.{tar.gz,whl} (venv_bquant/bin/python -m build); twine check PASSED для обоих; confirmation_index присутствует в wheel
[17:35:00] [included] [Files Modified] Коммит 3c95735 (pyproject.toml, bquant/__init__.py, CHANGELOG.md; submodule bquest не тронут) + аннотированный тег v0.0.2; пуш на origin (GitHub + GitLab)
[17:43:00] [included] [Technical] ~/.pypirc переведён из dotenv-стиля в корректный INI ([pypi]/[testpypi], username=__token__), права 600, бэкап ~/.pypirc.dotenv.bak
[17:50:00] [included] [Added] Публикация bquant 0.0.2 на боевой PyPI (twine upload); подтверждено: simple-индекс содержит оба файла, страница версии 200 — https://pypi.org/project/bquant/0.0.2/

[18:12:00] [not_included] [Added] pivot_points: confirmation_index = index + right_bars — точное fractal-подтверждение (N-бар паттерн завершается ровно через right_bars); хелпер _confirmation_index в bquant/analysis/zones/strategies/swing/pivot_points.py
[18:14:00] [not_included] [Added] find_peaks: confirmation_index = max(index + distance, бар prominence-ретрейса справа) — causal leak-free (оба условия необходимы для причинной детектируемости пика); хелпер _confirmation_index в bquant/analysis/zones/strategies/swing/find_peaks.py
[18:15:00] [not_included] [Changed] CACHE_SCHEMA_VERSION 2 → 3 в bquant/analysis/zones/pipeline.py (find_peaks/pivot_points теперь заполняют confirmation_index — изменение семантики кэшируемого вывода, по инварианту handoff)
[18:16:00] [not_included] [Technical] thresholds (_AdaptiveSwingStrategy) отдельной правки не требует — делегирует базовой стратегии в calculate_global, confirmation_index проходит насквозь (проверено на pivot_points/find_peaks)
[18:17:00] [not_included] [Added] Тесты test_pivot_points_confirmation_index_fractal и test_find_peaks_confirmation_index_causal в tests/unit/test_swing_global_calculation.py (инварианты: index < conf < n, distance/right_bars как нижняя граница)
[18:18:00] [not_included] [Technical] Sanity на tv_xauusd_1h: pivot_points 251/251 подтверждены (медианный лаг 2=right_bars), find_peaks 208/208 (медианный лаг 5=distance)

==================== COMMIT DIVIDER ====================
