import duckdb
import os

s3_key = os.getenv('S3_ACCESS_KEY', 's3admin')
s3_secret = os.getenv('S3_SECRET_KEY', 's3admin123')
s3_endpoint = os.getenv('S3_ENDPOINT', 'seaweedfs:8333') 

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"""
CREATE SECRET seaweed (
    TYPE s3, KEY_ID '{s3_key}', SECRET '{s3_secret}', 
    ENDPOINT '{s3_endpoint}', URL_STYLE 'path', USE_SSL false
);
""")

staging_path = 's3://staging/nyc-airbnb-listings/source_ingested_on=2026-11-03/staging.parquet'
mart_path = 's3://mart/nyc-airbnb-listings/source_ingested_on=2026-11-03/listings_metrics.parquet'

print("Building mart from staging...")

con.execute(f"""
    COPY (
        SELECT 
            neighbourhood_group,
            room_type,
            COUNT(*) AS listings_count,
            MEDIAN(price) AS median_price,
            AVG(availability_365) AS avg_availability
        FROM read_parquet('{staging_path}')
        WHERE price > 0 
        GROUP BY neighbourhood_group, room_type
    ) TO '{mart_path}' (FORMAT PARQUET);
""")

print("Mart saved successfully!")
print("\nVerification (first 5 rows):")
res = con.execute(f"SELECT * FROM read_parquet('{mart_path}') LIMIT 5").fetchall()
for row in res:
    print(row)