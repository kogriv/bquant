# Скрипт очистки проекта перед публикацией
# Удаляет временные файлы и папки сборки

Write-Host "🧹 Начинаем очистку проекта..." -ForegroundColor Green

# Функции для вывода с цветом
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# 1. Удаление папок сборки
Write-Status "Удаляем папки сборки..."
try {
    Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
    Write-Status "✓ build/ удалена"
} catch { Write-Warning "build/ не найдена или не может быть удалена" }

try {
    Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
    Write-Status "✓ dist/ удалена"
} catch { Write-Warning "dist/ не найдена или не может быть удалена" }

# 2. Удаление egg-info папок
Write-Status "Удаляем egg-info папки..."
try {
    Get-ChildItem -Path . -Recurse -Directory -Name "*.egg-info" | ForEach-Object {
        Remove-Item -Recurse -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "✓ *.egg-info папки удалены"
} catch { Write-Warning "*.egg-info папки не найдены или не могут быть удалены" }

# 3. Удаление файлов покрытия тестов
Write-Status "Удаляем файлы покрытия тестов..."
try {
    Remove-Item -Recurse -Force "htmlcov" -ErrorAction SilentlyContinue
    Write-Status "✓ htmlcov/ удалена"
} catch { Write-Warning "htmlcov/ не найдена или не может быть удалена" }

try {
    Remove-Item -Force ".coverage" -ErrorAction SilentlyContinue
    Write-Status "✓ .coverage удален"
} catch { Write-Warning ".coverage не найден или не может быть удален" }

try {
    Get-ChildItem -Path . -Name ".coverage.*" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "✓ .coverage.* файлы удалены"
} catch { Write-Warning ".coverage.* файлы не найдены или не могут быть удалены" }

# 4. Удаление кэша pytest
Write-Status "Удаляем кэш pytest..."
try {
    Remove-Item -Recurse -Force ".pytest_cache" -ErrorAction SilentlyContinue
    Write-Status "✓ .pytest_cache/ удалена"
} catch { Write-Warning ".pytest_cache/ не найдена или не может быть удалена" }

# 5. Удаление кэша Python
Write-Status "Удаляем кэш Python..."
try {
    Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object {
        Remove-Item -Recurse -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "✓ __pycache__ папки удалены"
} catch { Write-Warning "__pycache__ папки не найдены или не могут быть удалены" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*.pyc" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "✓ *.pyc файлы удалены"
} catch { Write-Warning "*.pyc файлы не найдены или не могут быть удалены" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*.pyo" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "✓ *.pyo файлы удалены"
} catch { Write-Warning "*.pyo файлы не найдены или не могут быть удалены" }

# 6. Удаление временных файлов редакторов
Write-Status "Удаляем временные файлы редакторов..."
try {
    Get-ChildItem -Path . -Recurse -File -Name "*.swp" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "✓ *.swp файлы удалены"
} catch { Write-Warning "*.swp файлы не найдены или не могут быть удалены" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*.swo" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "✓ *.swo файлы удалены"
} catch { Write-Warning "*.swo файлы не найдены или не могут быть удалены" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*~" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "✓ *~ файлы удалены"
} catch { Write-Warning "*~ файлы не найдены или не могут быть удалены" }

# 7. Проверка виртуальных окружений
Write-Warning "Проверяем виртуальные окружения..."
if (Test-Path "venv_kgrv_dell") {
    Write-Status "✓ venv_kgrv_dell найдено (НЕ удаляем - это ваше активное окружение)"
} else {
    Write-Warning "venv_kgrv_dell не найдено"
}

# 8. Финальная проверка
Write-Host ""
Write-Status "Проверяем результат очистки..."
$remainingFolders = @()
if (Test-Path "build") { $remainingFolders += "build" }
if (Test-Path "dist") { $remainingFolders += "dist" }
if (Test-Path "htmlcov") { $remainingFolders += "htmlcov" }
if (Test-Path ".pytest_cache") { $remainingFolders += ".pytest_cache" }

if ($remainingFolders.Count -gt 0) {
    Write-Error "Некоторые папки не были удалены: $($remainingFolders -join ', ')"
} else {
    Write-Status "✓ Очистка завершена успешно!"
}

# 9. Показываем размер проекта
Write-Host ""
Write-Status "Размер проекта после очистки:"
try {
    $size = (Get-ChildItem -Path . -Recurse -Force | Measure-Object -Property Length -Sum).Sum
    $sizeMB = [math]::Round($size / 1MB, 2)
    Write-Host "Размер: $sizeMB MB" -ForegroundColor Cyan
} catch {
    Write-Warning "Не удалось определить размер проекта"
}

Write-Host ""
Write-Status "Очистка завершена! Проект готов к сборке и публикации."
