# Примеры curl

Базовый URL локально: `http://127.0.0.1:8000`

## Health

```bash
curl -s http://127.0.0.1:8000/api/health
```

## Metrics

```bash
curl -s http://127.0.0.1:8000/api/metrics
```

## Contact (успех)

```bash
curl -s -X POST http://127.0.0.1:8000/api/contact \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Ivan Petrov\",\"phone\":\"+7 999 123-45-67\",\"email\":\"ivan@example.com\",\"comment\":\"Хочу обсудить backend интеграцию для проекта\"}"
```

## Contact (ошибка валидации)

```bash
curl -s -X POST http://127.0.0.1:8000/api/contact \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"A\",\"phone\":\"12\",\"email\":\"bad\",\"comment\":\"hi\"}"
```

## Swagger

Откройте в браузере: http://127.0.0.1:8000/api/docs/
