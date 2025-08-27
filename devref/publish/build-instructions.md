# Инструкции по сборке и публикации пакета KGRV

## 🚀 Готовность к сборке

Проект подготовлен к публикации! Выполните следующие шаги:

## 📋 Чек-лист перед сборкой

### ✅ Структура проекта готова:
- [x] LICENSE файл создан
- [x] MANIFEST.in исправлен
- [x] .gitignore обновлен
- [x] Entry points исправлены в setup.py
- [x] Старый CLI удален
- [x] CHANGELOG.md создан
- [x] Документация по публикации создана

## 🧹 Шаг 1: Очистка репозитория

**ВАЖНО:** Выполните очистку перед сборкой:

### Windows PowerShell:
```powershell
# Очистка временных файлов
Remove-Item -Recurse -Force build/ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist/ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force *.egg-info/ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force htmlcov/ -ErrorAction SilentlyContinue
Remove-Item -Force .coverage -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache/ -ErrorAction SilentlyContinue

# Очистка кэша Python
Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -File -Name "*.pyc" | Remove-Item -Force
```

## 📦 Шаг 2: Установка инструментов сборки

```bash
# В виртуальном окружении venv_kgrv_dell
pip install build twine
```

## 🔧 Шаг 3: Проверка пакета

```bash
# Установка в режиме разработки
pip install -e .

# Тестирование CLI
python -m kgrv.cli_click --help
python -m kgrv.cli_click info
python -m kgrv.cli_click validate

# Запуск тестов
python tests/test_about.py
```

## 📦 Шаг 4: Сборка пакета

```bash
# Сборка дистрибутивов
python -m build
```

Будут созданы файлы:
- `dist/kgrv-0.1.0.tar.gz` - исходный дистрибутив
- `dist/kgrv-0.1.0-py3-none-any.whl` - wheel дистрибутив

## ✅ Шаг 5: Проверка дистрибутивов

```bash
# Проверка качества дистрибутивов
twine check dist/*
```

Должен вывести: `Checking dist/* PASSED`

## 🧪 Шаг 6: Публикация на Test PyPI

### 6.1 Регистрация на Test PyPI
1. Перейдите на https://test.pypi.org/
2. Создайте аккаунт
3. Подтвердите email

### 6.2 Создание API токена
1. Войдите в Test PyPI
2. Account Settings → API tokens
3. Create token с scope "Entire account"
4. Сохраните токен

### 6.3 Загрузка на Test PyPI
```bash
# Загрузка на Test PyPI
twine upload --repository testpypi dist/*
# Введите:
# Username: __token__
# Password: ваш-токен-test-pypi
```

### 6.4 Проверка на Test PyPI
```bash
# Создайте новое окружение для теста
python -m venv test_env
test_env\Scripts\activate

# Установите с Test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ kgrv

# Тестируйте
python -c "import kgrv; print(kgrv.__version__)"
kgrv --help
kgrv info
```

## 🚀 Шаг 7: Публикация на PyPI

### 7.1 Регистрация на PyPI
1. Перейдите на https://pypi.org/
2. Создайте аккаунт
3. Подтвердите email

### 7.2 Создание API токена для PyPI
1. Войдите в PyPI
2. Account Settings → API tokens  
3. Create token с scope "Entire account"
4. Сохраните токен

### 7.3 Загрузка на PyPI
```bash
# Вернитесь в основное окружение
deactivate
venv_kgrv_dell\Scripts\activate

# Загрузка на PyPI
twine upload dist/*
# Введите:
# Username: __token__
# Password: ваш-токен-pypi
```

### 7.4 Финальная проверка
```bash
# Создайте новое окружение
python -m venv final_test
final_test\Scripts\activate

# Установите с PyPI
pip install kgrv

# Тестируйте
kgrv --version
kgrv demo
```

## 🎉 Шаг 8: После публикации

1. **Обновите README.md** - добавьте badges:
```markdown
[![PyPI version](https://badge.fury.io/py/kgrv.svg)](https://badge.fury.io/py/kgrv)
```

2. **Создайте релиз на GitHub**:
   - Перейдите в репозиторий
   - Releases → Create a new release
   - Tag: v0.1.0
   - Title: "First Release v0.1.0"
   - Описание из CHANGELOG.md

3. **Удалите временные файлы**:
```bash
rm BUILD_INSTRUCTIONS.md
rm CLEANUP_INSTRUCTIONS.md
```

## ⚠️ Возможные проблемы

### Имя пакета занято
```
ERROR: The name 'kgrv' conflicts with the name of an existing project
```
**Решение:** Измените name в setup.py на уникальное имя

### Ошибка аутентификации
```
ERROR: Invalid credentials
```
**Решение:** Проверьте токен, используйте `__token__` как username

### Ошибка зависимостей на Test PyPI
```
ERROR: No matching distribution found for requests
```
**Решение:** Используйте флаг `--extra-index-url https://pypi.org/simple/`

## 📊 Мониторинг после публикации

- **PyPI страница**: https://pypi.org/project/kgrv/
- **Статистика загрузок**: https://pypistats.org/packages/kgrv
- **GitHub релизы**: https://github.com/kogriv/kgrv/releases

Ваш пакет готов к публикации! 🎊
