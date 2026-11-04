# Фикстура парной статистики и плацебо

Контракт и генератор — у запросившей лаборатории. `units.csv` — 300 **синтетических** единиц
(`unit_id, month, variant, base, low, high`; месяц — ключ `год·12 + месяц − 1`, 2024-01 … 2025-12).
`expected.json` содержит:
- `paired` и `contrast` при сидах 1–3 для `boot_share` и `normal`;
- `placebo`: `sign_flip` и `permute_flags` при сидах 1–3, 200 перестановок;
- края: постоянная разность, пустая и малая группа, годы на границе `min_year_units`.

Результатов чьих-либо исследований здесь нет.

`tests/unit/test_paired_statistics_reproduce_the_reference.py` сверяет всё до `1e-9`, счётчики и
`placebo_p` — точно.
