# Developer Landing

Backend API и лендинг-презентация разработчика для тестового задания InternetLab.

Репозиторий: [github.com/Frame24/developer_landing](https://github.com/Frame24/developer_landing)

Полный цикл: `запрос → валидация → rate limit → AI → email/file fallback → ответ`.

Каркас сгенерирован через [cookiecutter-django](https://github.com/cookiecutter/cookiecutter-django), затем адаптирован под ТЗ: SQLite, contact API, AI (OpenRouter / OpenAI-compatible), лендинг, Render.

## 1. Как запустить

### Требования

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (рекомендуется) или pip
- API-ключ AI-провайдера (опционально; без ключа работает fallback)

### Установка (uv)

```bash
cd developer_landing
uv sync
cp .env.example .env
# заполните OPENAI_API_KEY и при необходимости OPENAI_BASE_URL
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

| URL | Что |
|---|---|
| http://127.0.0.1:8000/ | Лендинг с формой |
| http://127.0.0.1:8000/api/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/health | Healthcheck |
| http://127.0.0.1:8000/api/metrics | Статистика |

### Переменные окружения

См. `.env.example`. Ключевые:

| Переменная | Назначение |
|---|---|
| `DJANGO_SECRET_KEY` | Секрет Django |
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` / `config.settings.render` |
| `OPENAI_API_KEY` | Ключ провайдера (можно пустым: AI fallback) |
| `OPENAI_BASE_URL` | Базовый URL API. Для OpenRouter: `https://openrouter.ai/api/v1`. Пусто = официальный OpenAI |
| `OPENAI_MODEL` | Модель. Для OpenRouter free: `openrouter/free`. Для OpenAI: `gpt-4o-mini` |
| `OPENAI_TIMEOUT_SECONDS` | Таймаут AI (по умолчанию 20) |
| `EMAIL_HOST` / `EMAIL_*` | SMTP; если `EMAIL_HOST` пуст, письма пишутся в `storage/mail/` |
| `CONTACT_OWNER_EMAIL` | Получатель уведомления владельцу |
| `RATE_LIMIT_MAX` | Лимит запросов с IP (по умолчанию 5) |
| `RATE_LIMIT_WINDOW_SECONDS` | Окно лимита (по умолчанию 900) |

Пример для OpenRouter в `.env`:

```env
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openrouter/free
```

Ключ храните только в `.env` (файл в `.gitignore`), не в `.env.example` и не в git.

## 2. Стек технологий

**Backend**

- Python 3.12+
- Django 6 + Django REST Framework
- cookiecutter-django (каркас)
- django-environ, django-cors-headers, whitenoise, gunicorn
- drf-spectacular (OpenAPI / Swagger)
- SQLite (обращения) + файлы (логи, rate limit, metrics, mail fallback)

**AI**

- OpenAI-compatible SDK (`openai`)
- Провайдер: OpenRouter (бесплатные модели) или любой OpenAI-compatible endpoint через `OPENAI_BASE_URL`
- Классификация типа обращения
- Генерация ответа пользователю

**Frontend**

- Django templates + vanilla JS/CSS
- Лендинг с формой → `POST /api/contact`

**Инструменты разработки**

- Cursor (генерация и доработка кода)
- Git / GitHub

## 3. Архитектура

Слоистая структура внутри `developer_landing.contact`:

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
  examples/               # curl-примеры
  postman/                # Postman-коллекция
```

### Почему так

- **Django + DRF**: близко к вакансии (backend, API), быстрый OpenAPI через spectacular.
- **cookiecutter-django**: зрелый каркас (settings split, whitenoise, CORS, DRF).
- **SQLite + файлы**: достаточно для ТЗ, без отдельной БД/Redis на free-tier.
- **OpenAI-compatible client**: один код для OpenAI, OpenRouter и других провайдеров с тем же протоколом.
- **Services**: бизнес-логика не в views; проще читать и расширять.

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

Успех `201` (AI доступен):

```json
{
  "success": true,
  "data": {
    "id": 1,
    "ai_available": true,
    "request_type": "lead",
    "ai_reply": "Краткий ответ, сгенерированный моделью...",
    "email_via_smtp": false,
    "rate_limit_remaining": 4
  }
}
```

Если AI недоступен, те же поля приходят с `ai_available: false`, `request_type` / `ai_reply` = `null`; заявка всё равно принимается.

Статусы:

- `201` успех
- `400` ошибка валидации
- `429` rate limit (`Retry-After`)
- `500` внутренняя ошибка (не из-за AI)

Валидация: имя, телефон, email, комментарий (trim, формат телефона, длина комментария).

Примеры: [examples/curl.md](examples/curl.md), [postman/Developer_Landing_API.postman_collection.json](postman/Developer_Landing_API.postman_collection.json).

Где посмотреть ответ AI локально без SMTP:

- `storage/mail/user_*.txt` — копия пользователю (текст AI-ответа)
- `storage/mail/owner_*.txt` — уведомление владельцу (тип, `AI available`)

## 5. AI-интеграция

На каждый `POST /api/contact`:

1. **Классификация** типа: `lead | question | bug | partnership | other`
2. **Генерация ответа** пользователю (попадает в письмо-копию и в JSON `ai_reply`)

Клиент: `openai` SDK с опциональным `base_url` (`OPENAI_BASE_URL`), поэтому подходит OpenAI, OpenRouter и аналоги.

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

Классификация сначала пробует `response_format=json_object`; если модель не поддерживает, повтор без него и парсинг JSON из текста.

## 6. Что сделано с помощью AI

| Часть | Как | Что правил вручную |
|---|---|---|
| Каркас cookiecutter | CLI + зафиксированные ответы | Переход на SQLite, убрали psycopg/redis |
| Contact services/views | Cursor | Контракты ответов, статусы, fallback |
| OpenRouter / `base_url` | Cursor | Env, устойчивость classify без `json_object` |
| Лендинг CSS/JS | Cursor | Визуал, UX состояний формы |
| README / Postman | Cursor | Проверка фактов по коду |

Типовые промпты в Cursor: "слой Controllers → Services → Repositories", "graceful AI fallback", "OpenRouter через openai SDK", "лендинг без generic purple/cream".

## 7. Хранение данных

| Данные | Где |
|---|---|
| Обращения | SQLite (`ContactRequest`: тип, `ai_reply`, флаги) |
| Логи HTTP | `storage/logs/requests.log` (middleware) |
| Rate limit | `storage/rate_limit/rate_limit.json` |
| Метрики | `storage/metrics.json` + агрегаты из БД |
| Письма без SMTP | `storage/mail/*.txt` |

Rate limit: по умолчанию **5 запросов с IP за 15 минут** (`RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW_SECONDS`).

## Деплой на Render (бесплатно)

GitHub Pages не хостит Django. Используйте Render Free Web Service.

1. Запушьте репозиторий на GitHub.
2. На [render.com](https://render.com): New → Web Service → подключите репозиторий.
3. Build command: `./build.sh`
4. Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
5. Environment:

```
DJANGO_SETTINGS_MODULE=config.settings.render
DJANGO_SECRET_KEY=<длинный секрет>
DJANGO_ALLOWED_HOSTS=.onrender.com
PYTHON_VERSION=3.12.8
OPENAI_API_KEY=<ваш ключ>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openrouter/free
CONTACT_OWNER_EMAIL=<ваш email>
```

Можно использовать `render.yaml` как Blueprint (добавьте `OPENAI_BASE_URL` / `OPENAI_MODEL` в env вручную, если Blueprint их ещё не содержит).

После деплоя проверьте:

- `https://<app>.onrender.com/`
- `https://<app>.onrender.com/api/health`
- `https://<app>.onrender.com/api/docs/`

Free tier засыпает после простоя: первый запрос может идти 30–60 секунд.

**Публичный URL:** https://developer-landing-adae.onrender.com/

Если деплой недоступен, достаточно локального запуска по инструкции выше + Postman/curl.

## Лицензия

MIT
