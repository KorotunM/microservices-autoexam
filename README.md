# Учебный проект Autoexam (микросервисы на FastAPI)

Микросервисное приложение про финансы: авторизация, профили, финансы, уведомления и SPA-фронтенд. Все сервисы используют общий PostgreSQL, 
health-check эндпоинты и единые переменные окружения.

## Структура
- `services/auth-service` — FastAPI авторизация (`:8001`)
- `services/profile-service` — FastAPI профили (`:8002`)
- `services/finance-service` — FastAPI финансы (`:8003`)
- `services/notification-service` — FastAPI уведомления (`:8004`)
- `web-frontend` — SPA на FastAPI (прокси к сервисам, `:8080`, NodePort `30080`)
- `k8s` — манифесты для Kubernetes (namespace + configmaps + secrets + deployments/services)
- `db` — общие модели SQLAlchemy и Alembic миграции

## Порты сервисов
- auth-service: `8001`
- profile-service: `8002`
- finance-service: `8003`
- notification-service: `8004`
- web-frontend: `8080` (наружу через NodePort `30080`)
- postgres: `5432`

## Настройки
- Общая переменная: `DATABASE_URL` (`postgresql+asyncpg://postgres:postgres@postgres:5432/autoexam`)
- Логирование: `LOG_LEVEL` / `LOG_FORMAT` (stdout)
- auth-service: `JWT_SECRET`, `JWT_TTL_SECONDS`
- profile-service: `AUTH_VALIDATE_URL`
- finance-service: `AUTH_VALIDATE_URL`, `NOTIFICATION_URL`
- notification-service: опционально `DEFAULT_PAGE_SIZE`, `MAX_PAGE_SIZE`
- web-frontend: `LOGIN_TITLE`, `REGISTER_TITLE`, `WELCOME_MESSAGE`, `AUTH_BASE_URL`, `PROFILE_BASE_URL`, `FINANCE_BASE_URL`

## Сборка Docker-образов
Команды запускать из корня репозитория (контекст важен — нужен каталог `db`):
```bash
docker build -t autoexam/auth-service:latest -f services/auth-service/Dockerfile .
docker build -t autoexam/profile-service:latest -f services/profile-service/Dockerfile .
docker build -t autoexam/finance-service:latest -f services/finance-service/Dockerfile .
docker build -t autoexam/notification-service:latest -f services/notification-service/Dockerfile .
docker build -t autoexam/web-frontend:latest -f web-frontend/Dockerfile .
```

Если надо пересобрать образ:
```bash
kubectl rollout restart -n user-platform-exam deploy/auth-service
kubectl rollout restart -n user-platform-exam deploy/profile-service
kubectl rollout restart -n user-platform-exam deploy/finance-service
kubectl rollout restart -n user-platform-exam deploy/notification-service
kubectl rollout restart -n user-platform-exam deploy/web-frontend
```

## Запуск в Kubernetes (Docker Desktop)
1. Сначала создать namespace:
   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```
2. Применить остальные манифесты (configmaps, secrets, deployments, services):
   ```bash
   kubectl apply -f k8s/
   ```
3. Запустить миграции Alembic (Job внутри кластера):
   ```bash
   kubectl apply -f k8s/db-migrate-job.yaml
   ```
4. Посмотреть логи job:
   ```bash
   kubectl logs -n user-platform-exam job/db-migrate
   ```
   Опционально удалить job после успешного прогона:
   ```bash
   kubectl delete -f k8s/db-migrate-job.yaml
   ```
5. Проверить, что все сервисы готовы:
   ```bash
   kubectl get pods -n user-platform-exam
   kubectl get svc -n user-platform-exam
   ```

5.2. Посмотреть логи
   ```bash
   kubectl logs -n user-platform-exam deploy/profile-service -f   
   ```

6. Открыть фронтенд в браузере по NodePort:
   - Docker Desktop: `http://localhost:30080`
   - Или `http://<node-ip>:30080`

## Работа с БД и миграциями
- Модели и Alembic находятся в `db/`.
- Пример `.env` содержит `DATABASE_URL` и прочие переменные.
- Применить миграции (после установки зависимостей Alembic):
  ```bash
  export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/autoexam
  alembic upgrade head
  ```
- Базовая миграция `20251228_0001_init.py` создаёт таблицы `users`, `profiles`, `transactions`, `notification_logs` и индексы.

## Auth-service API (коротко)
- `POST /auth/register` `{username,password}` → 201 `{user_id, username}` (409 если занят)
- `POST /auth/login` `{username,password}` → 200 `{access_token, token_type:"bearer", expires_in}`
- `GET /auth/validate` + `Authorization: Bearer <token>` → 200 `{user_id, username}`

## Замечания
- Все манифесты используют namespace `user-platform-exam`, единые лейблы `app/component/tier/version`, 2 реплики у всех сервисов кроме Postgres.
- `web-frontend` — SPA, хранит JWT в `localStorage`, обращается к внутренним сервисам через `/api/*`, проксируемые самим фронтендом.
