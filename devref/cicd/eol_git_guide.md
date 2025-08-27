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
   ```
   git init
   ```
2. Добавьте удалённый репозиторий:
   ```
   git remote add origin https://github.com/kogriv/bquant.git
   ```
3. Создайте файл `.gitattributes` в корне проекта со следующим содержимым:
   ```
   * text=auto
   *.sh text eol=lf
   *.py text eol=lf
   *.md text eol=lf
   ```
4. Добавьте все файлы, включая `.gitattributes`:
   ```
   git add .
   ```
5. Сделайте коммит:
   ```
   git commit -m "Initial commit with .gitattributes for cross-platform EOL"
   ```
6. Пушьте на GitHub:
   ```
   git push -u origin main
   ```

---

## Порядок действий для ренормализации в рабочем проекте

1. Создайте или обновите `.gitattributes` в корне проекта (см. пример выше).
2. Добавьте файл:
   ```
   git add .gitattributes
   ```
3. Примените ренормализацию переводов строк:
   ```
   git add --renormalize .
   ```
4. Сделайте коммит:
   ```
   git commit -m "Add .gitattributes and normalize line endings"
   ```
5. Пушьте изменения:
   ```
   git push
   ```

---

## Примечания
- После этих действий Git будет автоматически поддерживать правильные переводы строк для всех платформ.
- Не требуется удалять и пересоздавать репозиторий.
- Для специфических файлов (например, shell-скрипты) можно явно указать `eol=lf`.
