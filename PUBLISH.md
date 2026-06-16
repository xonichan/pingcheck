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

## Настройка репозиториев

Перед использованием скриптов убедитесь, что добавлены удаленные репозитории:

```bash
git remote add gitverse https://gitverse.ru/project/pingcheck.git
git remote add github https://github.com/xonichan/pingcheck.git
```

Проверить настройку:
```bash
git remote -v
```
