# BQuant Project Cleanup Script
# Removes temporary files and build folders before publishing

param(
    [switch]$tst = $false,
    [switch]$vnv = $false,
    [switch]$vnva = $false,
    [switch]$vnvt = $false,
    [string[]]$vnvx = @()
)

Write-Host "Starting BQuant project cleanup..." -ForegroundColor Green

# Determine operation mode
$operationMode = "standard"
if ($vnva) {
    $operationMode = "venv_only"
    Write-Host "Virtual environments only mode - removing all venv_* folders" -ForegroundColor Yellow
} elseif ($vnv) {
    $operationMode = "full_with_venv"
    Write-Host "Full cleanup mode - removing all venv_* folders including production" -ForegroundColor Red
} elseif ($vnvt) {
    $operationMode = "test_venv_only"
    Write-Host "Test environments only mode - removing only test venv_* folders" -ForegroundColor Yellow
} elseif ($vnvx.Count -gt 0) {
    $operationMode = "specific_venv"
    Write-Host "Specific environments mode - removing: $($vnvx -join ', ')" -ForegroundColor Yellow
} elseif ($tst) {
    Write-Host "Test environments will be removed" -ForegroundColor Yellow
} else {
    Write-Host "Test environments will be preserved" -ForegroundColor Green
}

# Color output functions
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

# Function to handle virtual environments
function Remove-VirtualEnvironments {
    param(
        [string]$Mode,
        [string[]]$SpecificEnvs = @()
    )
    
    Write-Warning "Checking virtual environments..."
    $venvFolders = Get-ChildItem -Path . -Directory -Name "venv_*" -ErrorAction SilentlyContinue
    
    if ($venvFolders) {
        Write-Status "Found virtual environments: $($venvFolders -join ', ')"
        
        foreach ($venv in $venvFolders) {
            $shouldRemove = $false
            $reason = ""
            
            switch ($Mode) {
                "venv_only" {
                    $shouldRemove = $true
                    $reason = "all environments"
                }
                "full_with_venv" {
                    $shouldRemove = $true
                    $reason = "all environments (including production)"
                }
                "test_venv_only" {
                    $isTestEnv = $venv -match "test"
                    $shouldRemove = $isTestEnv
                    $reason = "test environment"
                }
                "specific_venv" {
                    $shouldRemove = $SpecificEnvs -contains $venv
                    $reason = "specified environment"
                }
                "standard" {
                    $isTestEnv = $venv -match "test"
                    $shouldRemove = $isTestEnv -and $tst
                    $reason = if ($isTestEnv) { "test environment" } else { "production environment" }
                }
            }
            
            if ($shouldRemove) {
                try {
                    Remove-Item -Recurse -Force $venv -ErrorAction Stop
                    Write-Status "Environment $venv removed ($reason)"
                } catch {
                    Write-Warning "Could not remove environment ${venv}: $($_.Exception.Message)"
                }
            } else {
                $preserveReason = if ($Mode -eq "standard" -and $venv -match "test") { " (use -tst to remove)" } else { "" }
                Write-Status "Environment $venv preserved$preserveReason"
            }
        }
    } else {
        Write-Warning "No venv_* environments found"
    }
}

# Handle virtual environments first if in venv-only modes
if ($operationMode -in @("venv_only", "test_venv_only")) {
    Remove-VirtualEnvironments -Mode $operationMode
    Write-Host ""
    Write-Status "Virtual environment cleanup completed!"
    exit 0
}

# 1. Remove build folders
Write-Status "Removing build folders..."
try {
    Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
    Write-Status "build/ removed"
} catch { Write-Warning "build/ not found or cannot be removed" }

try {
    Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
    Write-Status "dist/ removed"
} catch { Write-Warning "dist/ not found or cannot be removed" }

# 2. Remove egg-info folders
Write-Status "Removing egg-info folders..."
try {
    Get-ChildItem -Path . -Recurse -Directory -Name "*.egg-info" | ForEach-Object {
        Remove-Item -Recurse -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "*.egg-info folders removed"
} catch { Write-Warning "*.egg-info folders not found or cannot be removed" }

# 3. Remove test coverage files
Write-Status "Removing test coverage files..."
try {
    Remove-Item -Recurse -Force "htmlcov" -ErrorAction SilentlyContinue
    Write-Status "htmlcov/ removed"
} catch { Write-Warning "htmlcov/ not found or cannot be removed" }

try {
    Remove-Item -Force ".coverage" -ErrorAction SilentlyContinue
    Write-Status ".coverage removed"
} catch { Write-Warning ".coverage not found or cannot be removed" }

try {
    Get-ChildItem -Path . -Name ".coverage.*" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status ".coverage.* files removed"
} catch { Write-Warning ".coverage.* files not found or cannot be removed" }

# 4. Remove pytest cache
Write-Status "Removing pytest cache..."
try {
    Remove-Item -Recurse -Force ".pytest_cache" -ErrorAction SilentlyContinue
    Write-Status ".pytest_cache/ removed"
} catch { Write-Warning ".pytest_cache/ not found or cannot be removed" }

# 5. Remove Python cache
Write-Status "Removing Python cache..."
try {
    Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object {
        Remove-Item -Recurse -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "__pycache__ folders removed"
} catch { Write-Warning "__pycache__ folders not found or cannot be removed" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*.pyc" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "*.pyc files removed"
} catch { Write-Warning "*.pyc files not found or cannot be removed" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*.pyo" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "*.pyo files removed"
} catch { Write-Warning "*.pyo files not found or cannot be removed" }

# 6. Remove editor temporary files
Write-Status "Removing editor temporary files..."
try {
    Get-ChildItem -Path . -Recurse -File -Name "*.swp" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "*.swp files removed"
} catch { Write-Warning "*.swp files not found or cannot be removed" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*.swo" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "*.swo files removed"
} catch { Write-Warning "*.swo files not found or cannot be removed" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*~" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "*~ files removed"
} catch { Write-Warning "*~ files not found or cannot be removed" }

# 7. Remove IDE temporary files
Write-Status "Removing IDE temporary files..."
try {
    Remove-Item -Recurse -Force ".vscode" -ErrorAction SilentlyContinue
    Write-Status ".vscode/ removed"
} catch { Write-Warning ".vscode/ not found or cannot be removed" }

try {
    Remove-Item -Recurse -Force ".idea" -ErrorAction SilentlyContinue
    Write-Status ".idea/ removed"
} catch { Write-Warning ".idea/ not found or cannot be removed" }

# 8. Handle virtual environments
Remove-VirtualEnvironments -Mode $operationMode -SpecificEnvs $vnvx

# 9. Remove project temporary files
Write-Status "Removing project temporary files..."
try {
    Remove-Item -Recurse -Force "temp" -ErrorAction SilentlyContinue
    Write-Status "temp/ removed"
} catch { Write-Warning "temp/ not found or cannot be removed" }

try {
    Remove-Item -Recurse -Force "tmp" -ErrorAction SilentlyContinue
    Write-Status "tmp/ removed"
} catch { Write-Warning "tmp/ not found or cannot be removed" }

try {
    Remove-Item -Recurse -Force "logs" -ErrorAction SilentlyContinue
    Write-Status "logs/ removed"
} catch { Write-Warning "logs/ not found or cannot be removed" }

# 10. Remove profiling files
Write-Status "Removing profiling files..."
try {
    Get-ChildItem -Path . -Recurse -File -Name "*.prof" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "*.prof files removed"
} catch { Write-Warning "*.prof files not found or cannot be removed" }

try {
    Get-ChildItem -Path . -Recurse -File -Name "*.profile" | ForEach-Object {
        Remove-Item -Force $_ -ErrorAction SilentlyContinue
    }
    Write-Status "*.profile files removed"
} catch { Write-Warning "*.profile files not found or cannot be removed" }

# 11. Final check
Write-Host ""
Write-Status "Checking cleanup results..."
$remainingFolders = @()
if (Test-Path "build") { $remainingFolders += "build" }
if (Test-Path "dist") { $remainingFolders += "dist" }
if (Test-Path "htmlcov") { $remainingFolders += "htmlcov" }
if (Test-Path ".pytest_cache") { $remainingFolders += ".pytest_cache" }

if ($remainingFolders.Count -gt 0) {
    Write-Error "Some folders were not removed: $($remainingFolders -join ', ')"
} else {
    Write-Status "Cleanup completed successfully!"
}

# 12. Show project size
Write-Host ""
Write-Status "Project size after cleanup:"
try {
    $size = (Get-ChildItem -Path . -Recurse -Force | Measure-Object -Property Length -Sum).Sum
    $sizeMB = [math]::Round($size / 1MB, 2)
    Write-Host "Size: $sizeMB MB" -ForegroundColor Cyan
} catch {
    Write-Warning "Could not determine project size"
}

Write-Host ""
Write-Status "Cleanup completed! BQuant project is ready for build and publishing."
Write-Host ""
Write-Host "Usage examples:" -ForegroundColor Cyan
Write-Host "  .\cleanup.ps1                    - Standard cleanup (preserves test environments)" -ForegroundColor White
Write-Host "  .\cleanup.ps1 -tst              - Standard cleanup + remove test environments" -ForegroundColor White
Write-Host "  .\cleanup.ps1 -vnv              - Full cleanup + remove ALL environments" -ForegroundColor White
Write-Host "  .\cleanup.ps1 -vnva             - Remove ALL environments only (no other cleanup)" -ForegroundColor White
Write-Host "  .\cleanup.ps1 -vnvt             - Remove test environments only (no other cleanup)" -ForegroundColor White
Write-Host "  .\cleanup.ps1 -vnvx venv1,venv2 - Remove specific environments only" -ForegroundColor White
