REST API для управления организационной структурой компании с отделами и сотрудниками.

## Функциональность

- Управление отделами 
- Управление сотрудниками в отделах
- Каскадное удаление и перенос сотрудников при удалении отдела
- Валидация данных через Pydantic
- PostgreSQL + Django ORM
- Полная контейнеризация через Docker
- Набор автоматических тестов

## Технологический стек

- **Backend**: Django 5.0.6 + Django REST Framework
- **База данных**: PostgreSQL 15
- **Валидация**: Pydantic 2.7
- **Тестирование**: pytest + Django TestCase
- **Контейнеризация**: Docker + Docker Compose

### Установка и запуск

1. **Клонируйте репозиторий** (если нужно):
```bash
git clone https://github.com/Vivarlee/OrgApi
cd orgapi

# Сборка и запуск
docker-compose up --build

# Остановка
docker-compose down

# Запуск в режиме теста
docker-compose --profile testing run --rm test
