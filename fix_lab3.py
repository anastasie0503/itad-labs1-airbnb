import duckdb

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute("""
CREATE SECRET seaweed (
    TYPE s3, KEY_ID 's3admin', SECRET 's3admin123', 
    ENDPOINT 'seaweedfs:8333', URL_STYLE 'path', USE_SSL false
);
""")

raw_path = 's3://raw/nyc-airbnb-listings/ingested_on=2026-11-03/listings.csv'
staging_path = 's3://staging/nyc-airbnb-listings/source_ingested_on=2026-11-03/staging.parquet'
quarantine_path = 's3://staging/nyc-airbnb-listings/source_ingested_on=2026-11-03/quarantine.parquet'

print("--- 1. ПРОФИЛИРОВАНИЕ ---")
raw_count = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{raw_path}')").fetchone()[0]
null_price = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{raw_path}') WHERE price IS NULL").fetchone()[0]
print(f"Всего строк: {raw_count}, из них с пустой ценой (NULL): {null_price}")

print("\n--- 2. ПРОВЕРКИ КАЧЕСТВА ---")
dup_ids = con.execute(f"SELECT COUNT(*) FROM (SELECT id FROM read_csv_auto('{raw_path}') GROUP BY id HAVING COUNT(*) > 1)").fetchone()[0]
print(f"Правило 'unique_id': дубликатов ID: {dup_ids} (Действие: quarantine)")

bad_rooms = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{raw_path}') WHERE room_type NOT IN ('Entire home/apt', 'Private room', 'Shared room', 'Hotel room')").fetchone()[0]
print(f"Правило 'valid_room_type': неверный тип жилья: {bad_rooms} (Действие: report_only)")

bad_avail = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{raw_path}') WHERE availability_365 < 0 OR availability_365 > 365").fetchone()[0]
print(f"Правило 'valid_availability': дней доступности вне 0-365: {bad_avail} (Действие: flag)")

print(f"Правило 'not_null_price': пропусков цены: {null_price} (Действие: flag)")

bad_prices = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{raw_path}') WHERE price < 0").fetchone()[0]
print(f"Правило 'positive_price': отрицательных цен: {bad_prices} (Действие: quarantine)")


print("\n--- 3. СОХРАНЕНИЕ (С ИСПРАВЛЕНИЕМ NULL) ---")
# В карантин только отрицательные цены
con.execute(f"COPY (SELECT *, 'neg_price' as rule_id, 'Negative price' as reason FROM read_csv_auto('{raw_path}') WHERE price < 0) TO '{quarantine_path}' (FORMAT PARQUET);")

# В staging все остальные (включая NULL) + флаги
con.execute(f"""
    COPY (
        SELECT *,
            CASE WHEN price IS NULL THEN true ELSE false END as flag_null_price,
            CASE WHEN availability_365 < 0 OR availability_365 > 365 THEN true ELSE false END as flag_invalid_availability
        FROM read_csv_auto('{raw_path}')
        WHERE price >= 0 OR price IS NULL
    ) TO '{staging_path}' (FORMAT PARQUET);
""")

print("\n--- 4. ПРОВЕРКА БАЛАНСА ---")
staging_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{staging_path}')").fetchone()[0]
quarantine_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{quarantine_path}')").fetchone()[0]
print(f"Raw: {raw_count}, Staging: {staging_count}, Quarantine: {quarantine_count}")
print(f"Баланс (raw = staging + quarantine): {raw_count == (staging_count + quarantine_count)}")
print("\nГОТОВО!")