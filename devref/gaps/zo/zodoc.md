# Документационный аудит зонального анализа (zodoc)

**Версия:** 1.0  
**Дата:** 2025-10-21  
**Статус:** DRAFT – требуется выполнение плана  
**Контекст:** Подготовка полноценного обновления документации после внедрения архитектуры v2.1 (Truly Universal). Настоящий документ фиксирует фактическое состояние разделов документации и задаёт детальный перечень доработок/новых материалов.

---

## 1. Ключевые выводы (TL;DR)

1. **Фронт документации по-прежнему показывает монолит MACD.** Quick Start, главный `index.rst`, API-оглавление и большинство навигационных README демонстрируют `MACDZoneAnalyzer` как основной способ работы, хотя в коде он помечен как устаревший фасад и делегирует в универсальный пайплайн. 【F:docs/index.rst†L41-L55】【F:docs/user_guide/quick_start.md†L30-L154】【F:docs/api/README.md†L51-L108】【F:bquant/indicators/macd.py†L1-L156】
2. **Структура документации не соответствует фактическому содержимому.** README в разделах `examples/`, `tutorials/`, `developer_guide/` и `visualization/` ссылаются на подкаталоги и статьи, которых нет в репозитории. Аналогично, `docs/api/analysis/zones.md` содержит устаревшее описание `ZoneAnalyzer` вместо универсального пайплайна. 【F:docs/examples/README.md†L9-L199】【F:docs/tutorials/README.md†L9-L116】【F:docs/developer_guide/README.md†L9-L200】【F:docs/api/analysis/zones.md†L249-L304】
3. **Новые возможности v2.1 не задокументированы системно.** В коде и тестах подтверждена автоматическая передача `indicator_context`, универсальный билдер `analyze_zones()`, а также требования к стратегиям, но ни один публичный документ не объясняет контракт и сценарии использования. 【F:bquant/analysis/zones/models.py†L29-L118】【F:bquant/analysis/zones/pipeline.py†L523-L619】【F:tests/integration/test_truly_universal_zones.py†L50-L125】【F:tests/unit/test_zone_detection_strategies.py†L548-L672】【F:tests/unit/test_zone_models.py†L79-L150】
4. **Примеры и расширенная документация по-прежнему завязаны на MACD.** Скрипты `examples/05`, `06`, `07` используют устаревший фасад и приватные методы вместо нового билда; разделы API по стратегиям, статистике, визуализации и индикаторам демонстрируют только MACD-сценарии. 【F:examples/05_strategies_demo.py†L13-L115】【F:examples/06_regression_demo.py†L13-L90】【F:examples/07_validation_demo.py†L14-L161】【F:docs/api/analysis/strategies.md†L622-L679】【F:docs/api/analysis/statistical.md†L26-L188】【F:docs/api/visualization/README.md†L123-L165】【F:docs/api/indicators/README.md†L15-L188】
5. **Документационный план 2025-10-13 был сознательно ограничен («минимально обновить»), поэтому в репозитории отсутствуют материалы, обещанные тем планом.** Настоящий документ заменяет прежний режим работы «минимум изменений» на полноценный roadmap. 【F:devref/gaps/DOCUMENTATION_UPDATE_PLAN.md†L1-L124】

---

## 2. Фактическая структура документации (статус по файлам)

Легенда: 🔴 – требуется серьёзное переписывание; 🟡 – точечные правки/синхронизация; 🟢 – актуально; 🆕 – файл нужно создать.

```
docs/
├── index.rst                         🔴  Быстрый пример на MACD, нет упоминания universal pipeline.
├── README.md                         🟢  Инструкция по сборке.
├── api/
│   ├── README.md                     🔴  Карта API ориентирована на MACD и не отражает новые модули.
│   ├── analysis/
│   │   ├── README.md                🔴  Примеры и ссылки завязаны на MACD.
│   │   ├── zones.md                 🔴  Нижняя часть описывает legacy `ZoneAnalyzer`/утилиты.
│   │   ├── strategies.md            🟡  Usage/Basic раздел опирается на `MACDZoneAnalyzer`.
│   │   ├── statistical.md           🟡  Примеры не используют universal pipeline, терминология старая.
│   │   └── base.md                  🟢  Соответствует текущему коду.
│   ├── core/
│   │   └── *.md                     🟡  Проверить перекрёстные ссылки после обновления API-навигатора.
│   ├── data/                        🟢  Соответствует модулям.
│   ├── indicators/
│   │   ├── README.md                🔴  Подразумевает «MACD + зоны» как основную возможность.
│   │   └── macd.md                  🟡  Нужен акцент на статусе фасада и ссылку на universal API.
│   ├── visualization/README.md      🔴  Ссылается на charts.md/zones.md, которых нет.
│   ├── extension_guide.md           🟡  В целом актуально, но потребуется cross-link на новый pipeline.
│   └── (нет файла) pipeline.md      🆕  Требуется отдельный материал о `ZoneAnalysisBuilder`/`UniversalZoneAnalyzer`.
├── user_guide/
│   ├── README.md                    🔴  Навигация ориентирована на MACD; отсутствует файл `core_concepts.md`.
│   └── quick_start.md               🔴  Шаги 3-5 и «Полный пример» используют устаревший фасад.
├── tutorials/README.md              🔴  Все ссылки ведут на несуществующие материалы.
├── developer_guide/README.md        🔴  Содержимое описывает Architecture/Testing/CI статьи, которых нет.
├── examples/README.md               🔴  Каталоги basic/advanced/real_world отсутствуют; примеры – на MACD.
└── Makefile/conf.py/...             🟢  Без изменений.

examples/
├── 02_macd_zone_analysis.py         🟡  Содержит секции «legacy vs new», оставить как миграционный пример.
├── 02a_universal_zones.py           🟡  Нужно расширить, чтобы служил главным reference.
├── 05_strategies_demo.py            🔴  Перейти на builder + публичный API зон без `_zone_to_dict`.
├── 06_regression_demo.py            🔴  Аналогично, убрать зависимость от фасада.
├── 07_validation_demo.py            🔴  Аналогично.
└── README.md                        🟡  Уже отражает универсальный набор, но требует синхронизации с docs/.
```

---

## 3. Что обязательно задокументировать (источники в коде и тестах)

1. **Контракт `indicator_context`:** описание полей, кто их заполняет, как используют стратегии и анализаторы. 【F:bquant/analysis/zones/models.py†L29-L118】【F:tests/unit/test_zone_detection_strategies.py†L548-L672】
2. **Universal Pipeline:** шаги `with_indicator()`, `detect_zones()`, `with_strategies()`, `analyze()`, `build()`; настройки кэша, DI стратегий. 【F:bquant/analysis/zones/pipeline.py†L523-L619】
3. **Доказательства универсальности:** интеграционные и модульные тесты с фиктивными индикаторами; статистика покрытий. 【F:tests/integration/test_truly_universal_zones.py†L50-L125】【F:tests/unit/test_zone_models.py†L79-L150】
4. **Статус фасада MACD:** явное предупреждение о деприкации и ссылка на новый путь миграции. 【F:bquant/indicators/macd.py†L1-L159】
5. **Расширенные возможности (регрессия, валидация, стратегии):** продемонстрировать сценарии вне MACD и объяснить, какие поля доступны стратегиям. 【F:examples/05_strategies_demo.py†L13-L115】【F:examples/06_regression_demo.py†L13-L90】【F:examples/07_validation_demo.py†L14-L161】
6. **Новый технический долг:** ранее документация сознательно «заморожена» (см. план 2025-10-13), теперь нужно снять ограничение и создать недостающие материалы. 【F:devref/gaps/DOCUMENTATION_UPDATE_PLAN.md†L15-L80】

---

## 4. План обновления (этапы и задачи)

### Этап 0 – Обновление навигации и входных точек (1 день)
1. **Переписать `docs/index.rst` и `user_guide/quick_start.md` с использованием universal pipeline, добавить блок «Legacy MACD wrapper».** Источники: `docs/index.rst`, `docs/user_guide/quick_start.md`, `bquant/indicators/macd.py`. 【F:docs/index.rst†L41-L55】【F:docs/user_guide/quick_start.md†L30-L154】【F:bquant/indicators/macd.py†L1-L159】
2. **Синхронизировать `docs/api/README.md`, `docs/examples/README.md`, `docs/tutorials/README.md`, `docs/developer_guide/README.md` с реальной структурой (удалить фиктивные ссылки, указать новые материалы).** 【F:docs/api/README.md†L51-L108】【F:docs/examples/README.md†L9-L199】【F:docs/tutorials/README.md†L9-L116】【F:docs/developer_guide/README.md†L9-L200】

### Этап 1 – Переосмысление раздела зонального анализа (2 дня)
1. **Создать новую страницу `docs/api/analysis/pipeline.md` (или переработать `zones.md`) с подробным описанием `ZoneAnalysisBuilder`, `ZoneAnalysisPipeline`, `UniversalZoneAnalyzer`, кеширования и DI стратегий.** Источники: `bquant/analysis/zones/pipeline.py`, `bquant/analysis/zones/analyzer.py`, интеграционные тесты. 【F:bquant/analysis/zones/pipeline.py†L523-L619】【F:tests/integration/test_truly_universal_zones.py†L50-L125】
2. **Обновить `docs/api/analysis/zones.md`: убрать legacy `Zone`, `find_support_resistance`, включить раздел про `indicator_context`, примеры для MACD/RSI/Stochastic/кастомных индикаторов, ссылку на новую страницу pipeline.** 【F:docs/api/analysis/zones.md†L249-L304】【F:bquant/analysis/zones/models.py†L29-L118】
3. **Обновить `docs/api/analysis/README.md` и `docs/api/analysis/strategies.md`:** заменить usage-примеры на цепочку builder, подчеркнуть универсальность стратегий, показать чтение `indicator_context`. 【F:docs/api/analysis/README.md†L118-L190】【F:docs/api/analysis/strategies.md†L622-L679】
4. **Скорректировать `docs/api/analysis/statistical.md`:** продемонстрировать получение `zones_features` из универсального пайплайна, обновить терминологию (например, `correlation_price_hist` → `correlation_price_indicator` согласно плану v2.1). 【F:docs/api/analysis/statistical.md†L26-L188】【F:tests/unit/test_zone_models.py†L79-L150】

### Этап 2 – Индикаторы и визуализация (1 день)
1. **Переписать `docs/api/indicators/README.md`:** выделить фабрику, внешние библиотеки, пояснить, что `MACDZoneAnalyzer` – совместимый фасад, и дать прямую ссылку на universal pipeline. 【F:docs/api/indicators/README.md†L15-L188】【F:bquant/indicators/macd.py†L1-L159】
2. **Актуализировать `docs/api/indicators/macd.md`:** вынести предупреждение о деприкации, добавить раздел «Миграция» с примерами builder + presets, убрать устаревшие вызовы. 【F:docs/api/indicators/macd.md†L9-L118】【F:bquant/indicators/macd.py†L1-L159】
3. **Переписать `docs/api/visualization/README.md`:** описать реальные классы (`FinancialCharts`, `ZoneVisualizer`, `StatisticalPlots`, `themes`), привести пример визуализации зон через данные universal pipeline. 【F:docs/api/visualization/README.md†L123-L165】

### Этап 3 – Навигация для advanced-пользователей (1 день)
1. **Создать/заменить содержимое `docs/tutorials/README.md`:** вместо несуществующих статей дать ссылки на готовые примеры (`examples/02a`, `05-07`) и будущие планы (можно добавить секцию TODO). 【F:docs/tutorials/README.md†L9-L116】【F:examples/README.md†L9-L199】
2. **Переработать `docs/developer_guide/README.md`:** оставить реальные инструкции (env, тесты, CI), убрать несуществующие файлы или создать placeholder в разделе devref. 【F:docs/developer_guide/README.md†L9-L200】
3. **Обновить `docs/examples/README.md`:** описать фактический набор `examples/*.py`, выделить `02a_universal_zones.py` как основной учебный сценарий и добавить перекрёстные ссылки на обновлённые API-разделы. 【F:examples/README.md†L9-L199】【F:examples/02a_universal_zones.py†L502-L520】

### Этап 4 – Примеры кода (1 день)
1. **Переписать `examples/05/06/07` на новый API** и удалить обращения к `_zone_to_dict`. Показать, как получать зоны через `analyze_zones(...).build()` и как извлекать признаки из `ZoneAnalysisResult`. 【F:examples/05_strategies_demo.py†L13-L115】【F:examples/06_regression_demo.py†L13-L90】【F:examples/07_validation_demo.py†L14-L161】
2. **Обновить в примерах комментарии/print-блоки, чтобы акцентировать `indicator_context` и универсальные стратегии.** Источники – модульные тесты на стратегии и `ZoneFeaturesAnalyzer`. 【F:tests/unit/test_zone_detection_strategies.py†L548-L672】【F:tests/unit/test_zone_models.py†L79-L150】

### Этап 5 – Кросс-ссылки и завершающие штрихи (0.5 дня)
1. **Добавить ссылки между API и руководствами (Quick Start ↔ pipeline ↔ стратегии ↔ статистика ↔ примеры).**
2. **Проверить Sphinx build, обновить оглавление `index.rst` и конфигурацию (`conf.py`), при необходимости включить новые файлы.**
3. **Обновить `README` верхнего уровня (при необходимости) с кратким пунктом «Документация покрывает universal pipeline v2.1».**

---

## 5. Ресурсы и источники информации

| Источник | Назначение |
|----------|------------|
| `devref/gaps/zo/zouni_v2.md` | Архитектура v2.1, контракт стратегий, планы расширения. 【F:devref/gaps/zo/zouni_v2.md†L1-L156】 |
| `devref/gaps/DOCUMENTATION_UPDATE_PLAN.md` | История предыдущих решений, показывает, что текущие пробелы – результат «минимального» обновления. 【F:devref/gaps/DOCUMENTATION_UPDATE_PLAN.md†L15-L124】 |
| Тесты (`tests/integration/test_truly_universal_zones.py`, `tests/unit/test_zone_detection_strategies.py`, `tests/unit/test_zone_models.py`) | Подтверждают работу `indicator_context`, универсальность стратегий и builder. 【F:tests/integration/test_truly_universal_zones.py†L50-L125】【F:tests/unit/test_zone_detection_strategies.py†L548-L672】【F:tests/unit/test_zone_models.py†L79-L150】 |
| Код (`bquant/analysis/zones/*.py`, `bquant/indicators/macd.py`) | Истина о текущей реализации, статус деприкации, обязательные поля. 【F:bquant/analysis/zones/pipeline.py†L523-L619】【F:bquant/analysis/zones/models.py†L29-L118】【F:bquant/indicators/macd.py†L1-L159】 |
| Примеры (`examples/*.py`) | Нужно синхронизировать с документацией, после правок станут живыми учебными материалами. 【F:examples/05_strategies_demo.py†L13-L115】【F:examples/06_regression_demo.py†L13-L90】【F:examples/07_validation_demo.py†L14-L161】 |

---

## 6. Ожидаемый результат

После выполнения плана документация должна:

1. **Прямо вести пользователя в универсальный пайплайн** (Quick Start, главная страница, API-референс).
2. **Объяснять контракт `indicator_context` и связь детектора/стратегий** на уровне API и примеров.
3. **Содержать актуальные навигационные разделы** без ссылок на несуществующие материалы.
4. **Демонстрировать расширенные возможности** (регрессия, валидация, альтернативные индикаторы) без обращения к устаревшему фасаду.
5. **Иметь единое дерево ссылок**: Quick Start → Pipeline → Strategies/Statistical → Examples/Tutorials → Developer Guide.

---

## 7. Следующие шаги

1. Утвердить данный документ как новый базовый план вместо «минимального» плана 2025-10-13.
2. Распараллелить Этапы 0–2 (они независимы) и назначить ответственных.
3. После завершения Этапов 0–4 выполнить Сфинкс-сборку и ревью, затем обновить `CHANGELOG`/`README` при необходимости.
4. Зафиксировать новые материалы в репозитории и поднять задачу на автоматическое тестирование документации (sphinx-build) в CI.

