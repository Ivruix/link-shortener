# Link Shortener Service

Сервис для сокращения ссылок.

Развернут с помощью Render здесь: https://link-shortener-2wab.onrender.com

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
