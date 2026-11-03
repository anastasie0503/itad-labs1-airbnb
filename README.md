# ITAD Labs

Сквозной учебный data-проект курса «Информационные технологии анализа данных».

## Контур данных

```text
Источник → raw в SeaweedFS → staging → mart → анализ и отчёт.
```

SeaweedFS хранит файлы. Airflow ожидает и скачивает HTTP-источник. PostgreSQL используется только как база метаданных
Airflow. DuckDB читает и записывает Parquet-объекты в SeaweedFS, а dbt задаёт SQL-модели. dbt запускается через `uv`, а не
как отдельный Docker-сервис.

SeaweedFS работает в одном контейнере в режиме `weed mini`. При запуске entrypoint готовит права тома и
переключается на пользователя `seaweed`, а `S3_BUCKET=raw,staging,mart` обеспечивает создание недостающих бакетов.
Существующие объекты сохраняются. Healthcheck проверяет подписанным S3-запросом доступность каждого бакета.
Размер внутренних томов SeaweedFS задан равным 256 МиБ, чтобы на небольшом локальном диске хватало томов для
служебных данных и всех трёх бакетов. Это не ограничение общего размера бакета.

После успешной проверки airflow scheduler применяет миграции метабазы и создаёт администратора из `.env`, затем начинает
работу. Airflow webserver запускается после успешной проверки heartbeat scheduler. Отдельные init-сервисы не нужны.

Используются стандартные порты SeaweedFS: S3 API доступен на `http://localhost:8333`, а файловый интерфейс — по адресу
`http://localhost:8888/buckets/`; в нём видны бакеты и их объекты. На хосте используются `S3_ENDPOINT`,
`S3_ACCESS_KEY` и `S3_SECRET_KEY` из `.env`, а Airflow получает подключение `s3_conn` с адресом
`http://seaweedfs:8333` внутри сети Compose.

## Команды

Команды ниже работают одинаково в PowerShell, macOS и Linux. Для `dbt` предварительно скопируйте
`dbt/profiles.yml.example` в `dbt/profiles.yml`.

```bash
uv run ruff check .

docker compose up --build -d
uv run --env-file .env dbt debug --project-dir dbt --profiles-dir dbt
uv run --env-file .env dbt build --project-dir dbt --profiles-dir dbt
uv run --env-file .env python scripts/read_raw.py --path "s3://raw/green_tripdata/ingested_on=2026-01-01/green_tripdata_2025-01.parquet"
docker compose down
```

## Структура

- `config/` — будущие правила качества.
- `data/source/` — неизменяемые Git-снимки для ручного fallback.
- `airflow/dags/` — DAG'и оркестрации.
- `src/` — код ingestion, проверки и анализа.
- `scripts/` — кроссплатформенные точки входа для локальных проверок.
- `dbt/` — dbt-модели, материализуемые во внешние Parquet-файлы SeaweedFS.
- `infra/` — место для инфраструктурных материалов следующих лабораторных работ.
