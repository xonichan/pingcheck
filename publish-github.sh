#!/bin/bash
# Скрипт публикации в GitHub

echo "Публикация в GitHub..."

# Проверка изменений
if ! git diff-index --quiet HEAD --; then
    echo "Обнаружены несохраненные изменения. Сделайте commit перед публикацией."
    exit 1
fi

# Пуш в GitHub
git push github master

echo "Публикация в GitHub завершена!"
