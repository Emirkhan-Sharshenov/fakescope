# 🚀 Развертывание на Render

## Как данные отзывов будут храниться

### Вариант 1: PostgreSQL (рекомендуется) ⭐

На Render есть встроенная поддержка PostgreSQL. Данные будут храниться в облаке и **никогда не потеряются**.

#### Шаги:

1. **Добавить PostgreSQL базу на Render:**
   - В Render.com: Dashboard → Create → PostgreSQL
   - Выбрать план (бесплатный доступен)
   - Скопировать `DATABASE_URL`

2. **Добавить переменную окружения:**
   - В Render: Перейти к Web Service
   - Settings → Environment Variables
   - Добавить: `DATABASE_URL` = (скопированная строка подключения)

3. **Готово!** 
   - Приложение автоматически подключится к БД
   - Все отзывы будут храниться в PostgreSQL
   - При перезагрузке сервера данные сохранятся

#### Где будут данные:
- ✅ **Таблица `visitors`** - логи всех посетителей
- ✅ **Таблица `feedback`** - все отзывы с рейтингами и комментариями
- ✅ Защищенное облачное хранилище Render
- ✅ Доступ через `/analytics/stats` API

---

### Вариант 2: Локальное хранилище (если нет БД)

Если не настроить PostgreSQL, система автоматически использует локальные файлы:
- `data/visitors.jsonl`
- `data/feedback.jsonl`

⚠️ **Проблема:** При перезагрузке Render сервера все файлы удаляются!

---

## Настройка Render

### Конфигурация для Web Service:

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
gunicorn app:app
```

**Environment:**
- `FLASK_ENV`: `production`
- `GROQ_API_KEY`: (ваш API ключ)
- `DATABASE_URL`: (если используете PostgreSQL)

### Структура проекта для Render:

```
.
├── app.py              ✅ Flask приложение
├── analytics.py        ✅ Система отзывов (поддержка PostgreSQL)
├── detector.py         ✅ Детектор новостей
├── index.html          ✅ Frontend
├── requirements.txt    ✅ Зависимости (с psycopg2-binary)
├── translations.json   ✅ Многоязычность
├── fakescope_finetuned/ ✅ BERT модель
└── .env               (не коммитить)
```

---

## API для получения статистики

### GET `/analytics/stats`

Получить все данные об отзывах:

```json
{
  "total_visitors": 150,
  "total_feedback": 42,
  "thumbs_up": 35,
  "thumbs_down": 7,
  "approval_rate": 83.3,
  "languages": {
    "ru": 25,
    "en": 12,
    "de": 5
  },
  "recent_comments": [
    {
      "rating": "up",
      "comment": "Отличный анализ!",
      "language": "ru"
    },
    {
      "rating": "down",
      "comment": "Ошибка в оценке",
      "language": "en"
    }
  ]
}
```

### POST `/feedback`

Отправить отзыв:

```bash
curl -X POST https://your-render-app.onrender.com/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "abc123",
    "rating": "up",
    "comment": "Очень полезно!",
    "lang": "ru"
  }'
```

---

## Проверка статуса

### GET `/status`

```bash
curl https://your-render-app.onrender.com/status
```

Вернет информацию о системе, включая статус БД.

---

## Логирование

Все ошибки логируются в консоль Render:

```
✅ PostgreSQL connected for analytics
⚠️ PostgreSQL failed: ... (используется локальное хранилище)
```

---

## Схема базы данных (PostgreSQL)

### Таблица `visitors`
```sql
CREATE TABLE visitors (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ip_hash VARCHAR(16),           -- Хеш IP для конфиденциальности
  user_agent VARCHAR(100),       -- Браузер пользователя
  language VARCHAR(5)            -- Язык (ru, en, de, fr, es, zh)
);
```

### Таблица `feedback`
```sql
CREATE TABLE feedback (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ip_hash VARCHAR(16),           -- Хеш IP
  analysis_id VARCHAR(100),      -- ID анализа
  rating VARCHAR(5),             -- 'up' или 'down'
  comment TEXT,                  -- Комментарий пользователя
  language VARCHAR(5)            -- Язык
);
```

---

## 🔒 Конфиденциальность

- ✅ IP адреса хешируются (не хранятся оригиналы)
- ✅ Комментарии лимитированы на 500 символов
- ✅ Все данные локальные на вашем сервере Render
- ✅ Нет отправки на третьи сервисы

---

## Трудности и решения

### Проблема: "psycopg2 not installed"
**Решение:** В requirements.txt уже добавлен `psycopg2-binary>=2.9.0`

### Проблема: "DATABASE_URL не установлена"
**Решение:** Система автоматически fallback на локальные JSONL файлы

### Проблема: "Данные потеряны при перезагрузке"
**Решение:** Настроить PostgreSQL на Render (см. выше)

---

## Рекомендации

1. ✅ **Используйте PostgreSQL** - не потеряете данные
2. ✅ **Регулярно проверяйте статистику** через `/analytics/stats`
3. ✅ **Мониторьте логи** в консоли Render
4. ✅ **Экспортируйте данные** периодически для резервной копии

---

**Версия:** 1.0  
**Дата:** 18 апреля 2024  
**Статус:** Готово к развертыванию на Render ✅
