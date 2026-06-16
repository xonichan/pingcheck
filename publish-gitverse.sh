#!/bin/bash
# Скрипт публикации в Gitverse

echo "Публикация в Gitverse..."

# Проверка изменений
if ! git diff-index --quiet HEAD --; then
    echo "Обнаружены несохраненные изменения. Сделайте commit перед публикацией."
    exit 1
fi

# Пуш в Gitverse
git push gitverse master

echo "Публикация в Gitverse завершена!"
