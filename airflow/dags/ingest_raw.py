from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import requests

# ==== НАСТРОЙКИ ДЛЯ AIRBNB ====
SOURCE_URL = "file:///opt/airflow/data/source/listings.csv"
SOURCE_FILENAME = "listings.csv"
DATASET_SLUG = "nyc-airbnb-listings"


def load_to_raw(ds, **kwargs):
    """Загружает файл в raw, если его ещё нет. Не создаёт бакет."""
    s3_hook = S3Hook(aws_conn_id="s3_conn")
    bucket = "raw"
    key = f"{DATASET_SLUG}/ingested_on={ds}/{SOURCE_FILENAME}"

    # 1. Проверка бакета (НЕ создаём)
    if not s3_hook.check_for_bucket(bucket):
        raise Exception(
            f"Бакет '{bucket}' не существует. Выполни: docker compose up -d"
        )

    # 2. Проверка существующего объекта 
    if s3_hook.check_for_key(key, bucket_name=bucket):
        print(f"Объект уже существует: s3://{bucket}/{key}. Пропускаю загрузку.")
        return f"s3://{bucket}/{key}"

        # 3. Скачивание и загрузка байтов
    print(f"Читаю: {SOURCE_URL}")
    if SOURCE_URL.startswith("file://"):
        local_path = SOURCE_URL.replace("file://", "")
        with open(local_path, "rb") as f:
            file_bytes = f.read()
    else:
        response = requests.get(SOURCE_URL, timeout=300)
        response.raise_for_status()
        file_bytes = response.content

    print(f"Загружаю в s3://{bucket}/{key} ({len(file_bytes)} байт)")
    s3_hook.load_bytes(
        file_bytes,
        key=key,
        bucket_name=bucket,
        replace=False,
    )
    return f"s3://{bucket}/{key}"


with DAG(
    dag_id="ingest_raw",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "student",
        "retries": 0,
    },
    tags=["lab-02", "airbnb"],
) as dag:
  

    load = PythonOperator(
        task_id="load_to_raw",
        python_callable=load_to_raw,
        op_kwargs={
            "source_url": SOURCE_URL,
            "filename": SOURCE_FILENAME,
            "dataset_slug": DATASET_SLUG,
        },
    )

  