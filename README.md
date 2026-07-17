# Developer Landing

Backend API и лендинг-презентация разработчика для тестового задания InternetLab.

Полный цикл: `запрос → валидация → rate limit → AI → email/file fallback → ответ`.

Каркас проекта сгенерирован через [cookiecutter-django](https://github.com/cookiecutter/cookiecutter-django), затем адаптирован под ТЗ (SQLite, contact API, AI, лендинг, Render).

## 1. Как запустить

### Требования

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (рекомендуется) или pip

### Установка (uv)

```bash
cd developer_landing
uv sync
cp .env.example .env
# при необходимости отредактируйте .env
uv run python manage.py migrate
uv run python manage.py runserver
```

### Установка (venv + pip)

```bash
cd developer_landing
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Откройте:

- Лендинг: http://127.0.0.1:8000/
- Swagger: http://127.0.0.1:8000/api/docs/
- Health: http://127.0.0.1:8000/api/health

### Переменные окружения

См. `.env.example`. Ключевые:

| Переменная | Назначение |
|---|---|
| `DJANGO_SECRET_KEY` | Секрет Django |
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` / `config.settings.render` |
| `OPENAI_API_KEY` | Ключ OpenAI (можно пустым: AI fallback) |
| `OPENAI_MODEL` | По умолчанию `gpt-4o-mini` |
| `EMAIL_HOST` / `EMAIL_*` | SMTP; если `EMAIL_HOST` пуст, письма пишутся в `storage/mail/` |
| `CONTACT_OWNER_EMAIL` | Получатель уведомления владельцу |
| `RATE_LIMIT_MAX` | Лимит запросов с IP (по умолчанию 5) |
| `RATE_LIMIT_WINDOW_SECONDS` | Окно лимита (по умолчанию 900) |

## 2. Стек технологий

**Backend**

- Python 3.12+
- Django 6 + Django REST Framework
- cookiecutter-django (каркас)
- django-environ, django-cors-headers, whitenoise, gunicorn
- drf-spectacular (OpenAPI / Swagger)
- SQLite (обращения) + файлы (логи, rate limit, metrics, mail fallback)

**AI**

- OpenAI API (`openai` SDK), модель `gpt-4o-mini`
- Классификация типа обращения
- Генерация ответа пользователю

**Frontend**

- Django templates + vanilla JS/CSS
- Лендинг с формой, которая бьёт в `POST /api/contact`

**Инструменты разработки**

- Cursor (генерация и доработка кода)
- Git

## 3. Архитектура

Слоистая структура внутри приложения `developer_landing.contact`:

```
Views (controllers)
  → Serializers (валидация)
  → Services (бизнес-логика)
  → Repositories / File handlers (хранение)
```

```
developer_landing/
  config/                 # settings, urls, wsgi
  developer_landing/
    contact/
      views.py            # Controllers
      serializers.py
      services/           # Contact, AI, Email, RateLimit, Metrics
      repositories/       # ORM + JSON file store
      middleware.py       # Логирование запросов
      exception_handler.py
    templates/pages/      # Лендинг
    static/               # CSS/JS лендинга
  storage/                # logs, mail, rate_limit, metrics
```

### Почему так

- **Django + DRF**: близко к вакансии (backend, API), быстрый OpenAPI через spectacular.
- **cookiecutter-django**: зрелый каркас (settings split, whitenoise, CORS, DRF).
- **SQLite + файлы**: достаточно для ТЗ, без отдельной БД/Redis на free-tier.
- **Services**: бизнес-логика не в views; проще тестировать и читать.

## 4. Реализация API

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/contact` | Форма обратной связи |
| `GET` | `/api/health` | Статус сервиса |
| `GET` | `/api/metrics` | Статистика обращений |
| `GET` | `/api/docs/` | Swagger UI |
| `GET` | `/api/schema/` | OpenAPI schema |

### `POST /api/contact`

Тело:

```json
{
  "name": "Ivan Petrov",
  "phone": "+7 999 123-45-67",
  "email": "ivan@example.com",
  "comment": "Хочу обсудить backend интеграцию"
}
```

Успех `201`:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "ai_available": false,
    "request_type": null,
    "ai_reply": null,
    "email_via_smtp": false,
    "rate_limit_remaining": 4
  }
}
```

Статусы:

- `201` успех
- `400` ошибка валидации
- `429` rate limit
- `500` внутренняя ошибка (не из-за AI)

Валидация: имя, телефон, email, комментарий (санитизация/trim, проверка формата телефона).

Примеры: [examples/curl.md](examples/curl.md), [postman/Developer_Landing_API.postman_collection.json](postman/Developer_Landing_API.postman_collection.json).

## 5. AI-интеграция

На каждый `POST /api/contact`:

1. **Классификация** типа: `lead | question | bug | partnership | other`
2. **Генерация ответа** пользователю (попадает в письмо-копию)

### Fallback

Если нет `OPENAI_API_KEY`, таймаут или ошибка провайдера:

- сервис **не падает**
- `ai_available: false`
- письма уходят с шаблонным ответом
- метрика `ai_fallback` увеличивается

### Промпты

См. `developer_landing/contact/services/ai_service.py`:

- `CLASSIFY_PROMPT`: JSON с `request_type` и `confidence`
- `REPLY_PROMPT`: короткий вежливый ответ на русском без выдуманных обещаний

## 6. Что сделано с помощью AI

| Часть | Как | Что правил вручную |
|---|---|---|
| Каркас cookiecutter | CLI + зафиксированные ответы | Переход на SQLite, убрали psycopg/redis |
| Contact services/views | Cursor | Контракты ответов, статусы, fallback |
| Лендинг CSS/JS | Cursor | Визуал, UX состояний формы |
| README / Postman | Cursor | Проверка фактов по коду |

Типовые промпты в Cursor: "слой Controllers → Services → Repositories", "graceful AI fallback", "лендинг без generic purple/cream".

## 7. Хранение данных

| Данные | Где |
|---|---|
| Обращения | SQLite (`ContactRequest`) |
| Логи HTTP | `storage/logs/requests.log` (middleware) |
| Rate limit | `storage/rate_limit/rate_limit.json` |
| Метрики | `storage/metrics.json` + агрегаты из БД |
| Письма без SMTP | `storage/mail/*.txt` |

Rate limit: по умолчанию **5 запросов с IP за 15 минут**.

## Деплой на Render (бесплатно)

GitHub Pages **не** хостит Django. Используйте Render Free Web Service.

1. Создайте GitHub-репозиторий и запушьте содержимое `developer_landing/`.
2. На [render.com](https://render.com): New → Web Service → подключите репозиторий.
3. Build command: `./build.sh` (или `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate --no-input`).
4. Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
5. Environment:

```
DJANGO_SETTINGS_MODULE=config.settings.render
DJANGO_SECRET_KEY=<длинный секрет>
DJANGO_ALLOWED_HOSTS=.onrender.com
PYTHON_VERSION=3.12.8
OPENAI_API_KEY=<ваш ключ>
CONTACT_OWNER_EMAIL=<ваш email>
```

Можно использовать `render.yaml` как Blueprint.

После деплоя проверьте:

- `https://<app>.onrender.com/`
- `https://<app>.onrender.com/api/health`
- `https://<app>.onrender.com/api/docs/`

Free tier засыпает после простоя: первый запрос может идти 30–60 секунд.

Если деплой недоступен, достаточно локального запуска по инструкции выше + Postman/curl.

## Лицензия

MIT
