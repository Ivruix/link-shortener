# Link Shortener Service

Сервис для сокращения ссылок.

Развернут с помощью Render здесь: https://link-shortener-2wab.onrender.com

Документация: https://link-shortener-2wab.onrender.com/docs

## Дополнительный функционал

- Автоматическое удаление неиспользуемых ссылок (каждые 30 дней)
- Отображение истории всех истекших ссылок с информацией о них
- Создание коротких ссылок для незарегистрированных пользователей

## Запуск

```bash
docker-compose up --build
```

Сервис будет доступен на http://localhost:8000

## API Документация

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

## Тестирование

### Покрытие тестами

Текущее покрытие кода тестами: `90%`

Отчет pytest: `htmlcov/index.html`

Отчет locust: `locust-report.html`

### Запуск тестов

```bash
# Запустить все тесты (с покрытием и html отчетом)
pytest
```

### Запуск нагрузочных тестов

```bash
# Запустить сервисы
docker-compose up -d

# Запустить нагрузочное тестирование
locust -f tests/load/locustfile.py --headless --users 30 --spawn-rate 2 --run-time 1m --host http://localhost:8000 --html locust-report.html

# Остановить сервисы после тестирования
docker-compose down
```

## Описание API

### Авторизация

- `POST /auth/register` - Регистрация нового пользователя
  - Body: `{"username": "user", "password": "pass"}`

- `POST /auth/login` - Вход и получение JWT токена
  - Body: `{"username": "user", "password": "pass"}`

### Ссылки

- `POST /links/shorten` - Создать короткую ссылку (доступно всем)
  - Body: `{"original_url": "https://example.com", "custom_alias": "mylink", "expires_at": "2048-12-31T23:59:59"}`
  - Опционально: `Authorization: Bearer <token>` для привязки к аккаунту

- `GET /links/{short_code}` - Перенаправление на оригинальный URL

- `PUT /links/{short_code}` - Обновить ссылку (только владелец)
  - Header: `Authorization: Bearer <token>`
  - Body: `{"original_url": "https://newurl.com"}`

- `DELETE /links/{short_code}` - Удалить ссылку (только владелец)
  - Header: `Authorization: Bearer <token>`

- `GET /links/{short_code}/stats` - Статистика ссылки

- `GET /links/search?original_url=https://example.com` - Поиск по оригинальному URL

- `GET /links/expired` - История удаленных ссылок (только авторизованные)
short_code>

## Пример использования

1. Зарегистрируйтесь:
```bash
curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d '{"username":"testuser","password":"testpass"}'
```

2. Создайте ссылку (без авторизации):
```bash
curl -X POST http://localhost:8000/links/shorten -H "Content-Type: application/json" -d '{"original_url":"https://google.com"}'
```

Или с авторизацией (для привязки к аккаунту):
```bash
curl -X POST http://localhost:8000/links/shorten -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"original_url":"https://google.com"}'
```

3. Перейдите по ссылке:
```bash
curl http://localhost:8000/links/<short_code>
```

## Описание БД

**users** - пользователи
- `id` - уникальный идентификатор
- `username` - имя пользователя
- `hashed_password` - хешированный пароль

**links** - активные ссылки
- `id` - уникальный идентификатор
- `short_code` - короткий код
- `original_url` - оригинальный URL
- `user_id` - владелец ссылки (может быть NULL для анонимных)
- `created_at` - дата создания
- `expires_at` - дата истечения
- `last_accessed_at` - дата последнего перехода
- `access_count` - количество переходов

**expired_links** - удаленные ссылки
- `id` - уникальный идентификатор
- `short_code` - короткий код
- `original_url` - оригинальный URL
- `user_id` - владелец ссылки
- `created_at` - дата создания
- `expired_at` - дата удаления
- `deletion_reason` - причина удаления (expired, unused, manual)
