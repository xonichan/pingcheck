#!/bin/bash
# Скрипт публикации в Gitverse и GitHub (PowerShell equivalent)

Write-Host "Публикация в Gitverse и GitHub..." -ForegroundColor Cyan

# Проверка изменений
$changed = git diff-index --quiet HEAD --
if ($LASTEXITCODE -ne 0) {
    Write-Host "Обнаружены несохраненные изменения. Сделайте commit перед публикацией." -ForegroundColor Red
    exit 1
}

# Пуш в Gitverse
Write-Host "Отправка в Gitverse..." -ForegroundColor Yellow
git push gitverse master

# Пуш в GitHub
Write-Host "Отправка в GitHub..." -ForegroundColor Yellow
git push github master

Write-Host "Публикация завершена! Оба репозитория обновлены." -ForegroundColor Green
