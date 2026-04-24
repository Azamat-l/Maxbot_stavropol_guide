# Max бот‑гид по туристическим местам Ставропольского края

## Что это

Production-шаблон чат-бота для мессенджера **Max** (Bot API `platform-api.max.ru`) в режиме **Webhook**:
- Категории / фильтры / карточки мест
- Избранное (SQLite/Postgres)
- Callback-кнопки (через `POST /answers`)
- Контент в `data/attractions.json` с горячей перезагрузкой
- Админ-функции: загрузка изображений, импорт CSV, регистрация webhook

## Требования

- Сервер с Docker и Docker Compose
- Доменное имя (например, через DuckDNS или другой DDNS)
- Аккаунт в мессенджере Max с токеном бота

## Развертывание на сервере

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/MAX_bot_Hotkey.git
cd MAX_bot_Hotkey
```

### 2. Настройка переменных окружения

Скопируйте пример файла окружения и заполните его:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл:

- `MAX_BOT_TOKEN`: Ваш токен бота из Max (получите в личном кабинете Max)
- `MAX_WEBHOOK_SECRET`: Секретный ключ для webhook (придумайте сложный)
- `PUBLIC_BASE_URL`: Публичный URL вашего сервера (например, `https://your-domain.com`)
- `WEBHOOK_PATH`: Путь для webhook (по умолчанию `/webhook/max`)
- `DATABASE_URL`: URL базы данных (SQLite по умолчанию: `sqlite+aiosqlite:///./var/app.db` или Postgres: `postgresql+asyncpg://user:pass@host:5432/dbname`)
- `ADMIN_API_KEY`: Ключ для админ-API (придумайте)
- `RATE_LIMIT_PER_MINUTE`: Лимит запросов в минуту (по умолчанию 60)
- `LOG_LEVEL`: Уровень логирования (INFO, DEBUG и т.д.)

### 3. Настройка домена и SSL

- Зарегистрируйте домен или используйте DDNS (например, DuckDNS).
- Обновите `Caddyfile`, заменив `stavropollocalguide.duckdns.org` на ваш домен.
- Caddy автоматически получит SSL-сертификат от Let's Encrypt.

### 4. Запуск с Docker Compose

Если используете SQLite (по умолчанию):

```bash
docker-compose up -d
```

Если используете Postgres:

```bash
docker-compose --profile postgres up -d
```

Это запустит:
- Приложение бота (порт 8080 внутри контейнера)
- Caddy прокси (порты 80 и 443)
- Postgres (если включен, порт 5432)

### 5. Проверка развертывания

- Проверьте здоровье: `curl https://your-domain.com/healthz`
- Логи: `docker-compose logs -f app`

### 6. Регистрация webhook в Max

После запуска выполните регистрацию webhook:

```bash
docker-compose exec app python -m app.admin.register_webhook
```

Это создаст подписку на события в Max API.

## Управление контентом

### Обновление данных

- Отредактируйте `data/attractions.json`
- Перезагрузите контент:
  - CLI: `docker-compose exec app python -m app.admin.reload_content`
  - HTTP: `curl -X POST https://your-domain.com/admin/reload-content -H "X-Admin-Key: your-admin-key"`

### Загрузка изображений

1. Положите картинки в `data/photos/` на сервере.
2. Пропишите в JSON: `"photo_local": "data/photos/image.jpg"`
3. Загрузите в Max и обновите JSON:

```bash
docker-compose exec app python -m app.admin.upload_images
```

### Импорт из CSV

```bash
docker-compose exec app python -m app.admin.import_csv path/to/file.csv
```

## Локальный запуск (для разработки)

1. Установите Python 3.11+
2. Создайте виртуальное окружение:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# или source .venv/bin/activate  # Linux/Mac
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Настройте `.env` (см. выше)
5. Запустите:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

6. Для webhook: `python -m app.admin.register_webhook`

## Docker

- `Dockerfile`: Сборка образа приложения
- `docker-compose.yml`: Оркестрация сервисов
- `Caddyfile`: Конфигурация прокси

## API эндпоинты

- `GET /healthz`: Проверка здоровья
- `POST /webhook/max`: Webhook от Max
- `POST /admin/reload-content`: Перезагрузка контента (требует `X-Admin-Key`)

## Безопасность

- Используйте сильные ключи для `MAX_WEBHOOK_SECRET` и `ADMIN_API_KEY`
- Настройте firewall для ограничения доступа к портам
- Регулярно обновляйте Docker-образы

## Поддержка

Если возникли проблемы, проверьте логи: `docker-compose logs`

