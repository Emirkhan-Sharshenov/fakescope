## 📋 ИТОГОВЫЙ ОТВЕТ: Данные на Render

### ❓ Вопрос: Куда будут отправлены отзывы, статистика, лайки и дизлайки?

---

## ✅ Ответ: Зависит от конфигурации

### **Вариант 1: PostgreSQL (рекомендуется)** ⭐

Если вы добавите `DATABASE_URL` в Render:
- 📊 **Таблица `visitors`** - все посетители (IP хеш, браузер, язык, время)
- ⭐ **Таблица `feedback`** - все отзывы (👍/👎 рейтинг + комментарий)
- 🔒 **Облачное хранилище** на Render PostgreSQL
- ⚡ **Никогда не потеряются** - даже при перезагрузке

**Как добавить PostgreSQL:**
1. Render.com → Create → PostgreSQL
2. Скопировать `DATABASE_URL`
3. В Web Service: Environment Variables → добавить `DATABASE_URL`

---

### **Вариант 2: Локальные файлы (fallback)** 

Если `DATABASE_URL` не установлена:
- 📄 **`data/visitors.jsonl`** - логи посетителей
- 💬 **`data/feedback.jsonl`** - отзывы пользователей
- ⚠️ **ПРОБЛЕМА:** При перезагрузке Render сервера все данные удаляются!

---

## 🎯 Совместимость с Render

### Изменения совместимы? ✅ ДА

| Компонент | Совместимость | Статус |
|-----------|--------------|--------|
| app.py | ✅ Полностью совместим | Отслеживание посетителей работает |
| analytics.py | ✅ Поддержка PostgreSQL + fallback | Автоматическое переключение |
| HTML/JS | ✅ Работает на сервере | Кнопки 👍👎 на клиенте |
| requirements.txt | ✅ Добавлен psycopg2-binary | Поддержка БД автоматическая |

---

## 📊 API для отзывов

### **POST `/feedback`** - Отправить отзыв
```bash
curl -X POST https://your-app.onrender.com/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "abc123",
    "rating": "up",          # "up" или "down"
    "comment": "Отличный анализ!",
    "lang": "ru"
  }'
```

### **GET `/analytics/stats`** - Получить статистику
```bash
curl https://your-app.onrender.com/analytics/stats
```

**Ответ:**
```json
{
  "total_visitors": 150,
  "total_feedback": 42,
  "thumbs_up": 35,
  "thumbs_down": 7,
  "approval_rate": 83.3,
  "languages": {"ru": 25, "en": 12},
  "recent_comments": [...]
}
```

---

## 🚀 Как развернуть на Render

### 1️⃣ Подготовка
- ✅ Все файлы готовы (app.py, analytics.py)
- ✅ requirements.txt обновлен
- ✅ render.yaml создан для автодеплоя

### 2️⃣ На Render Dashboard
```
1. Создать Web Service (GitHub синхронизация)
2. Build Command: pip install -r requirements.txt
3. Start Command: gunicorn app:app
4. Добавить Environment Variables:
   - GROQ_API_KEY: (ваш ключ)
   - FLASK_ENV: production
   - DATABASE_URL: (опционально, для PostgreSQL)
```

### 3️⃣ PostgreSQL (опционально, но рекомендуется)
```
1. Render → Create → PostgreSQL
2. Выбрать план (бесплатный доступен)
3. Скопировать DATABASE_URL
4. В Web Service добавить переменную DATABASE_URL
```

---

## 📁 Структура данных

### **На Render (если PostgreSQL):**
```sql
-- Таблица посетителей
visitors:
  - id, timestamp, ip_hash, user_agent, language

-- Таблица отзывов
feedback:
  - id, timestamp, ip_hash, analysis_id, rating, comment, language
```

### **На Render (если локально):**
```
data/
  ├── visitors.jsonl    (может потеряться)
  └── feedback.jsonl    (может потеряться)
```

---

## 🔒 Конфиденциальность

- ✅ IP адреса хешируются (SHA256, не хранятся оригиналы)
- ✅ Комментарии лимитированы на 500 символов
- ✅ Все данные остаются на вашем сервере Render
- ✅ Нет отправки на третьи сервисы

---

## 📚 Документация

Подробная информация в файлах:
- [`RENDER_SETUP.md`](RENDER_SETUP.md) - Полная инструкция по развертыванию
- [`FEEDBACK_SYSTEM.md`](FEEDBACK_SYSTEM.md) - Описание системы отзывов
- [`README.md`](README.md) - Общая информация о проекте

---

## ✨ Итог

| Что | Где хранится | Статус |
|-----|-------------|---------|
| 👤 Посетители | PostgreSQL на Render или data/visitors.jsonl | ✅ Отслеживаются |
| 👍 Лайки | PostgreSQL на Render или data/feedback.jsonl | ✅ Сохраняются |
| 👎 Дизлайки | PostgreSQL на Render или data/feedback.jsonl | ✅ Сохраняются |
| 💬 Комментарии | PostgreSQL на Render или data/feedback.jsonl | ✅ Сохраняются |
| 📊 Статистика | `/analytics/stats` API | ✅ Доступна |

**Рекомендация:** Используйте PostgreSQL на Render для надежного хранения данных! 🚀
