# CHANGE TRACE LOG — 2026-09-06

[Сверка codemap: граф пересобран на 0.0.12 — вне репозитория, только `.codemap/` в gitignore]

[not_included] [Technical] Граф `.codemap/graph.json` пересобран из `977f915` инструментом codmap 0.0.12 (`build bquant --deep --repeat 3 --mode full`, те же четыре `--consumer` и `--docs`): 5100 узлов / 14287 рёбер, `samples: runs 3, unstable 9`, схема 0.13; удалённый `_find_any_oscillator` не находится, `lilliefors_normal`/`explain_zone_duration`/`calculate_atr`/`MetricSpec` находятся. Сборка ~2 мин, 300 МБ. Артефакт в gitignore, в репо не входит

[Релиз 0.0.13]

[included] [Changed] pyproject.toml, bquant/__init__.py, uv.lock — версия 0.0.12 → 0.0.13
[included] [Changed] CHANGELOG.md — `[Unreleased]` → `[0.0.13] - 2026-09-06`: вводный абзац с гейтом, «Ломающие изменения одним списком» (CACHE_VERSION 26, колонка `atr`, отказ от угадывания осциллятора, `explain_*`, `lilliefors`, протоколы стратегий, MIGRATION_v2.md), «Известные ограничения» (G64–G67, G48, custom-MACD/`adjust`, формы словарей валидатора, только OOS в пайплайне, регрессия ex post); запись о `DiskCache.clear()` из гейта волны 5
[not_included] [Technical] Гейт содержимого релиза = гейт волны 5 на `977f915` (чистый клон, оба плеча 3322/33/0, батарея 35/35); релизный коммит меняет только версию, CHANGELOG и uv.lock — повторно не гоняется (правило с 0.0.12)

==================== COMMIT DIVIDER ====================
