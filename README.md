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
```
