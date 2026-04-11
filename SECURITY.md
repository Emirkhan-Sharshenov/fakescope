# 🔐 Защита секретов

## Что было сделано

1. ✅ **Создан `.gitignore`** — исключает файлы с секретами и данными
2. ✅ **Создан `.env.example`** — шаблон переменных окружения (можно загружать на GitHub)
3. ✅ **Создан `.env`** — реальные секреты (в `.gitignore`, не загружается на GitHub)
4. ✅ **Обновлен `detector.py`** — теперь загружает ключи из переменных окружения
5. ✅ **Обновлен `requirements.txt`** — добавлена зависимость `python-dotenv`

## 🛡️ Как использовать

### Локально (для разработки)
```bash
# Скопировать шаблон
cp .env.example .env

# Отредактировать .env и добавить свой реальный GROQ_API_KEY
nano .env
# или в VS Code: Ctrl+O → .env

# Запустить приложение
python app.py
```

### На GitHub
- Загружай только `.env.example` (без реальных секретов)
- `.env` будет автоматически игнорирован благодаря `.gitignore`

### На сервере (Production)
Установи переменные окружения через:
- **Heroku**: Settings → Config Vars
- **Vercel**: Settings → Environment Variables  
- **Railway/Render**: Environment → Add Variable
- **Docker**: ENV или --env флаги
- **Linux server**: экспорт в `/etc/environment` или `.bashrc`

```bash
export GROQ_API_KEY="твой_реальный_ключ"
python app.py
```

## ⚠️ Внимание

Если ты уже залил секреты на GitHub, нужно:
1. **Переключить API ключ** на новый (старый больше не безопасен!)
2. Удалить историю из git:
```bash
git filter-branch --tree-filter 'rm -f .env' HEAD
git push --force
```

## 📋 Что теперь в `.gitignore`

- `.env` — локальные секреты ❌ не загружается
- `__pycache__/` — кэш Python
- `.venv/` — виртуальное окружение  
- `.vscode/`, `.idea/` — настройки IDE
- `*.log` — логи

---
✅ Теперь твои секреты в безопасности!
