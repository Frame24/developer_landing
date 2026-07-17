# Developer Landing

Backend API и лендинг-презентация разработчика для тестового задания InternetLab.

Репозиторий: [github.com/Frame24/developer_landing](https://github.com/Frame24/developer_landing)

Полный цикл: `запрос → валидация → rate limit → AI → email/file fallback → ответ`.

Каркас сгенерирован через [cookiecutter-django](https://github.com/cookiecutter/cookiecutter-django), затем адаптирован под ТЗ: SQLite, contact API, AI (OpenRouter / OpenAI-compatible), лендинг, Render.

**Публичный URL:** https://developer-landing-adae.onrender.com/

## 1. Как запустить

### Требования

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (рекомендуется) или pip
- API-ключ AI-провайдера (опционально; без ключа работает fallback)
- Git

### Локальный запуск (пошагово)

1. Клонировать репозиторий и перейти в каталог проекта:

```bash
git clone https://github.com/Frame24/developer_landing.git
cd developer_landing
```

2. Создать `.env` из примера:

```bash
cp .env.example .env
```

На Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

3. В `.env` для локали оставьте как минимум:

```env
DJANGO_READ_DOT_ENV_FILE=True
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=local-dev-secret-change-me-please-32chars
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CONTACT_OWNER_EMAIL=owner@example.com
```

Опционально:

- AI: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` (без ключа форма всё равно работает)
- Email: блок Resend из `.env.example` (без него письма пишутся только в `storage/mail/`)

4. Установить зависимости и поднять сервер (один из двух способов).

#### Вариант A: uv

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

#### Вариант B: venv + pip

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

5. Открыть в браузере:

| URL | Что |
|---|---|
| http://127.0.0.1:8000/ | Лендинг с формой |
| http://127.0.0.1:8000/api/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/health | Healthcheck |
| http://127.0.0.1:8000/api/metrics | Статистика |
| http://127.0.0.1:8000/api/mail | Демо-лента сохранённых писем |

6. Быстрая проверка API без браузера:

```bash
curl -s http://127.0.0.1:8000/api/health

curl -s -X POST http://127.0.0.1:8000/api/contact \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Ivan Petrov\",\"phone\":\"+7 999 123-45-67\",\"email\":\"ivan@example.com\",\"comment\":\"Хочу обсудить backend интеграцию для проекта\"}"
```

После отправки формы смотрите копии писем в `storage/mail/` (и в панели на лендинге).

Остановка сервера: `Ctrl+C` в терминале.

### Переменные окружения

См. `.env.example`. Ключевые:

| Переменная | Назначение |
|---|---|
| `DJANGO_SECRET_KEY` | Секрет Django |
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` / `config.settings.render` |
| `OPENAI_API_KEY` | Ключ провайдера (можно пустым: AI fallback) |
| `OPENAI_BASE_URL` | Базовый URL API. Для OpenRouter: `https://openrouter.ai/api/v1` |
| `OPENAI_MODEL` | Модель. Для OpenRouter free: `openrouter/free` |
| `OPENAI_TIMEOUT_SECONDS` | Таймаут AI (по умолчанию 20) |
| `EMAIL_HOST` / `EMAIL_*` | Если `EMAIL_HOST` пуст, письма только в `storage/mail/` |
| `CONTACT_OWNER_EMAIL` | Получатель уведомления владельцу |
| `EMAIL_DEMO_FORCE_TO` | Демо: оба письма на один адрес (см. раздел про почту) |
| `RATE_LIMIT_MAX` | Лимит запросов с IP (по умолчанию 5) |
| `RATE_LIMIT_WINDOW_SECONDS` | Окно лимита (по умолчанию 900) |

Пример для OpenRouter:

```env
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openrouter/free
```

Пример для Resend (рекомендуется для локали с VPN и для Render):

```env
EMAIL_HOST=smtp.resend.com
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=re_...
DJANGO_DEFAULT_FROM_EMAIL=Developer Landing <onboarding@resend.dev>
CONTACT_OWNER_EMAIL=you@example.com
EMAIL_DEMO_FORCE_TO=you@example.com
```

Ключ храните только в `.env` (файл в `.gitignore`), не в git.

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
- Провайдер: OpenRouter (бесплатные модели) или любой OpenAI-compatible endpoint
- Классификация типа обращения + генерация ответа пользователю

**Email**

- Resend HTTPS API (если `EMAIL_HOST` содержит `resend`) или Django SMTP
- Файловый fallback `storage/mail/`

**Frontend**

- Django templates + vanilla JS/CSS
- Лендинг с формой → `POST /api/contact`, демо-ящик писем, виджет `/api/metrics`

**Инструменты**

- Cursor (генерация и доработка), Git / GitHub, uv

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
- **SQLite + файлы**: достаточно для ТЗ, без Redis на free-tier.
- **OpenAI-compatible client**: один код для OpenAI / OpenRouter.
- **Services**: бизнес-логика не в views.
- **Синхронный приём заявки, асинхронный AI+email**: `201` сразу после валидации и записи в БД; классификация, ответ и письма догоняют в фоне (удобнее UX, меньше риск таймаута gunicorn на Render).

## 4. Реализация API

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/contact` | Форма обратной связи |
| `GET` | `/api/health` | Статус сервиса |
| `GET` | `/api/metrics` | Статистика обращений |
| `GET` | `/api/mail` | Демо: сохранённые копии писем |
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

Успех `201` (заявка принята; AI и email ещё могут идти в фоне):

```json
{
  "success": true,
  "data": {
    "id": 1,
    "ai_available": false,
    "request_type": null,
    "ai_reply": null,
    "email_via_smtp": false,
    "email_queued": true,
    "email_owner_to": "owner@example.com",
    "email_user_to": "ivan@example.com",
    "rate_limit_remaining": 4
  }
}
```

Через несколько секунд результат AI и письма появляются в БД, `storage/mail/`, `GET /api/mail` и на лендинге. Если AI недоступен, письма уходят с шаблонным текстом, метрика `ai_fallback` растёт.

Статусы:

- `201` успех
- `400` ошибка валидации
- `429` rate limit (`Retry-After`)
- `500` внутренняя ошибка (не из-за AI)

Валидация: имя, телефон, email, комментарий (trim, формат телефона, длина комментария).

Примеры: [examples/curl.md](examples/curl.md), [postman/Developer_Landing_API.postman_collection.json](postman/Developer_Landing_API.postman_collection.json).

Где посмотреть письма локально:

- `storage/mail/user_*.txt` — копия пользователю (текст AI-ответа)
- `storage/mail/owner_*.txt` — уведомление владельцу
- на лендинге: панель "Панель тестового задания" / `GET /api/mail`

### Email: owner + user

В нормальном режиме:

- письмо владельцу → `CONTACT_OWNER_EMAIL`
- копия пользователю → email из формы

Оба текста всегда пишутся в `storage/mail/` (даже если SMTP/API недоступен).

### Ограничения почты (важно для демо)

1. **Gmail / Mail.ru SMTP** часто блокируют отправку с VPN и с IP датацентров (Render). Локально без VPN иногда работает, на Render обычно нет.
2. Поэтому для демо выбран **Resend**. Если `EMAIL_HOST` содержит `resend`, код шлёт через **HTTPS** `https://api.resend.com/emails` (порт 587 SMTP с VPN часто таймаутится).
3. **Resend без своего домена** может доставлять только на email аккаунта Resend. Для проверки ставьте:
   - `EMAIL_DEMO_FORCE_TO=<email аккаунта Resend>`
   - тогда **оба** письма (owner + user) уходят на этот адрес; в теле письма видно исходный email из формы.
4. С верифицированным доменом в Resend уберите `EMAIL_DEMO_FORCE_TO`: owner и user снова разъедутся по разным адресам.

## 5. AI-интеграция

На каждый `POST /api/contact`:

1. **Классификация** типа: `lead | question | bug | partnership | other` (сначала правила по ключевым словам, затем LLM при `other`)
2. **Генерация ответа** пользователю (письмо-копия; в JSON `ai_reply` появится после фоновой обработки, если смотреть повторно через admin/БД)

Клиент: `openai` SDK с опциональным `base_url` (`OPENAI_BASE_URL`).

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
| Каркас cookiecutter | CLI | Переход на SQLite, убрали лишнее |
| Contact services/views | Cursor | Контракты ответов, статусы, fallback |
| OpenRouter / `base_url` | Cursor | Env, устойчивость classify |
| Resend HTTPS + demo force-to | Cursor | Обход VPN/SMTP, разделение owner/user |
| Лендинг CSS/JS + почтовый ящик | Cursor | UX формы, демо-панель |
| README / Postman | Cursor | Сверка с кодом и ТЗ |

Типовые промпты в Cursor: "слой Controllers → Services → Repositories", "graceful AI fallback", "OpenRouter через openai SDK".

## 7. Хранение данных

| Данные | Где |
|---|---|
| Обращения | SQLite (`ContactRequest`: тип, `ai_reply`, флаги) |
| Логи HTTP | `storage/logs/requests.log` (middleware) |
| Rate limit | `storage/rate_limit/rate_limit.json` |
| Метрики | `storage/metrics.json` + агрегаты из БД |
| Копии писем | `storage/mail/*.txt` (всегда) + Resend/SMTP при настройке |

Rate limit: по умолчанию **5 запросов с IP за 15 минут** (`RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW_SECONDS`).

Глобальный error handler DRF: `developer_landing/contact/exception_handler.py`  
CORS: `django-cors-headers`  
OpenAPI: `/api/docs/`

## Деплой на Render

1. Репозиторий на GitHub.
2. [render.com](https://render.com): New → Web Service.
3. Build: `./build.sh`
4. Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2`
5. Environment (минимум):

```
DJANGO_SETTINGS_MODULE=config.settings.render
DJANGO_SECRET_KEY=<длинный секрет>
DJANGO_ALLOWED_HOSTS=.onrender.com
PYTHON_VERSION=3.12.8
OPENAI_API_KEY=<ключ>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openrouter/free
EMAIL_HOST=smtp.resend.com
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=re_...
DJANGO_DEFAULT_FROM_EMAIL=Developer Landing <onboarding@resend.dev>
CONTACT_OWNER_EMAIL=<email аккаунта Resend>
EMAIL_DEMO_FORCE_TO=<email аккаунта Resend>
```

После деплоя:

- https://developer-landing-adae.onrender.com/
- https://developer-landing-adae.onrender.com/api/health
- https://developer-landing-adae.onrender.com/api/docs/

Free tier засыпает после простоя: первый запрос 30–60 секунд. Диск эфемерный: `storage/mail` на Render сбрасывается при редеплое.

Если деплой недоступен, достаточно локального запуска + Postman/curl.

## Лицензия

MIT
