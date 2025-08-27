# Справка: Переводы строк (LF/CRLF) и кроссплатформенность в Git

## Проблема

На Windows по умолчанию используется формат перевода строк CRLF, на Linux/macOS — LF. Git может автоматически конвертировать строки, что иногда вызывает предупреждения и проблемы совместимости.
```cmd
warning: in the working copy of 'bquant/data/samples/__init__.py', LF will be replaced by CRLF the next time Git touches it
```

## Решение

Для кроссплатформенных проектов рекомендуется использовать файл `.gitattributes`, чтобы явно задать правила для переводов строк.

---

## Порядок действий при создании нового репозитория (с нуля)

1. Инициализируйте репозиторий:
```bash
git init
```
2. Добавьте удалённый репозиторий:
```bash
git remote add origin https://github.com/kogriv/bquant.git
```
3. Создайте файл `.gitattributes` в корне проекта со следующим содержимым:
```bash
* text=auto
*.sh text eol=lf
*.py text eol=lf
*.md text eol=lf
```
4. Добавьте все файлы, включая `.gitattributes`:
```bash
git add .
```
5. Сделайте коммит:
```bash
git commit -m "Initial commit with .gitattributes for cross-platform EOL"
```
6. Выбор ветки:
```bash
git branch -M main
```

6. Пушьте на GitHub:
```bash
git push -u origin main
```

---

## Порядок действий для ренормализации в рабочем проекте

1. Создайте или обновите `.gitattributes` в корне проекта (см. пример выше).
2. Добавьте файл:
```bash
git add .gitattributes
```
3. Примените ренормализацию переводов строк:
```bash
git add --renormalize .
```
4. Сделайте коммит:
```bash
git commit -m "Add .gitattributes and normalize line endings"
```
5. Пушьте изменения:
```bash
git push
```

---

## Примечания
- После этих действий Git будет автоматически поддерживать правильные переводы строк для всех платформ.
- Не требуется удалять и пересоздавать репозиторий.
- Для специфических файлов (например, shell-скрипты) можно явно указать `eol=lf`.
