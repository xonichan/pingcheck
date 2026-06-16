# Скрипты публикации

Следующие скрипты упрощают публикацию проекта в Gitverse и GitHub:

## Важно: Ручное создание репозитория

Gitverse требует ручного создания репозитория через веб-интерфейс:

1. Перейти на https://gitverse.ru/
2. Нажать "Создать проект"
3. Указать имя `pingcheck` и описание
4. После создания скопировать URL репозитория
5. Обновить URL в файле `.urls.txt` или скриптах

## Bash скрипты

- `publish.sh` - публикация в оба репозитория (Gitverse и GitHub)
- `publish-gitverse.sh` - публикация только в Gitverse
- `publish-github.sh` - публикация только в GitHub

**Использование:**
```bash
chmod +x publish*.sh
./publish.sh
```

## PowerShell скрипты

- `publish.ps1` - публикация в оба репозитория

**Использование:**
```powershell
.\publish.ps1
```

## Настройка репозиториев

Перед использованием скриптов убедитесь, что добавлены удаленные репозитории:

```bash
git remote add gitverse https://gitverse.ru/USER/pingcheck.git
git remote add github https://github.com/xonichan/pingcheck.git
```

Проверить настройку:
```bash
git remote -v
```

**Примечание:** Gitverse требует авторизации и может иметь ограничения на push. Для публикации в Gitverse может потребоваться использовать веб-интерфейс или настроить SSH-ключи.

## Контакты

- [Gitverse](https://gitverse.ru/nicholasrogov)
- [GitHub](https://github.com/xonichan)
