# Скрипты публикации

Следующие скрипты упрощают публикацию проекта в Gitverse и GitHub:

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

**Примечание:** Gitverse может требовать ручной публикации через веб-интерфейс из-за ограничений на push. Проверьте права доступа перед использованием скриптов.

## Настройка репозиториев

Перед использованием скриптов убедитесь, что добавлены удаленные репозитории:

```bash
git remote add gitverse https://gitverse.ru/nicholasrogov/pingcheck.git
git remote add github https://github.com/xonichan/pingcheck.git
```

Проверить настройку:
```bash
git remote -v
```

**Примечание:** Gitverse требует авторизации и может иметь ограничения на push. Для публикации в Gitverse может потребоваться использовать веб-интерфейс или настроить SSH-ключи.
