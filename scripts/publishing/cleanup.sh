#!/bin/bash

# Скрипт очистки проекта BQuant перед публикацией
# Удаляет временные файлы и папки сборки

echo "🧹 Начинаем очистку проекта BQuant..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Удаление папок сборки
print_status "Удаляем папки сборки..."
rm -rf build/ 2>/dev/null && print_status "✓ build/ удалена"
rm -rf dist/ 2>/dev/null && print_status "✓ dist/ удалена"

# 2. Удаление egg-info папок
print_status "Удаляем egg-info папки..."
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null && print_status "✓ *.egg-info папки удалены"

# 3. Удаление файлов покрытия тестов
print_status "Удаляем файлы покрытия тестов..."
rm -rf htmlcov/ 2>/dev/null && print_status "✓ htmlcov/ удалена"
rm -f .coverage 2>/dev/null && print_status "✓ .coverage удален"
rm -f .coverage.* 2>/dev/null && print_status "✓ .coverage.* файлы удалены"

# 4. Удаление кэша pytest
print_status "Удаляем кэш pytest..."
rm -rf .pytest_cache/ 2>/dev/null && print_status "✓ .pytest_cache/ удалена"

# 5. Удаление кэша Python
print_status "Удаляем кэш Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null && print_status "✓ __pycache__ папки удалены"
find . -name "*.pyc" -delete 2>/dev/null && print_status "✓ *.pyc файлы удалены"
find . -name "*.pyo" -delete 2>/dev/null && print_status "✓ *.pyo файлы удалены"

# 6. Удаление временных файлов редакторов
print_status "Удаляем временные файлы редакторов..."
find . -name "*.swp" -delete 2>/dev/null && print_status "✓ *.swp файлы удалены"
find . -name "*.swo" -delete 2>/dev/null && print_status "✓ *.swo файлы удалены"
find . -name "*~" -delete 2>/dev/null && print_status "✓ *~ файлы удалены"

# 7. Удаление временных файлов IDE
print_status "Удаляем временные файлы IDE..."
rm -rf .vscode/ 2>/dev/null && print_status "✓ .vscode/ удалена"
rm -rf .idea/ 2>/dev/null && print_status "✓ .idea/ удалена"

# 8. Проверка виртуальных окружений
print_warning "Проверяем виртуальные окружения..."
if [ -d "venv_bquant_dell" ]; then
    print_status "✓ venv_bquant_dell найдено (НЕ удаляем - это ваше активное окружение)"
else
    print_warning "venv_bquant_dell не найдено"
fi

# 9. Удаление временных файлов проекта
print_status "Удаляем временные файлы проекта..."
rm -rf temp/ 2>/dev/null && print_status "✓ temp/ удалена"
rm -rf tmp/ 2>/dev/null && print_status "✓ tmp/ удалена"
rm -rf logs/ 2>/dev/null && print_status "✓ logs/ удалена"

# 10. Удаление файлов профилирования
print_status "Удаляем файлы профилирования..."
find . -name "*.prof" -delete 2>/dev/null && print_status "✓ *.prof файлы удалены"
find . -name "*.profile" -delete 2>/dev/null && print_status "✓ *.profile файлы удалены"

# 11. Финальная проверка
echo ""
print_status "Проверяем результат очистки..."
if [ -d "build" ] || [ -d "dist" ] || [ -d "htmlcov" ] || [ -d ".pytest_cache" ]; then
    print_error "Некоторые папки не были удалены!"
    ls -la | grep -E "(build|dist|htmlcov|\.pytest_cache)" 2>/dev/null || true
else
    print_status "✓ Очистка завершена успешно!"
fi

# 12. Показываем размер проекта
echo ""
print_status "Размер проекта после очистки:"
du -sh . 2>/dev/null || echo "Не удалось определить размер"

echo ""
print_status "Очистка завершена! Проект BQuant готов к сборке и публикации."
