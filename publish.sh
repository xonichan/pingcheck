#!/bin/bash
# Скрипт публикации в Gitverse и GitHub

echo "Публикация в Gitverse и GitHub..."

# Проверка изменений
if ! git diff-index --quiet HEAD --; then
    echo "Обнаружены несохраненные изменения. Сделайте commit перед публикацией."
    exit 1
fi

# Пуш в Gitverse
echo "Отправка в Gitverse..."
git push gitverse master

# Пуш в GitHub
echo "Отправка в GitHub..."
git push github master

echo "Публикация завершена! Оба репозитория обновлены."
