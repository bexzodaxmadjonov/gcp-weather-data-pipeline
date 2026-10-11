import csv 
import io
import json
import logging
from datetime import datetime, timezone, timedelta

from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.sdk import DAG, task, Param

log = logging.getLogger("airflow.task")

PROJECT_ID = "cloud-practice-510608"
BRONZE_BUCKET = "cloud-practice-510608-weather-lake-bronze"
SILVER_BUCKET = "cloud-practice-510608-weather-lake"
BQ_TABLE = f"{PROJECT_ID}.weather.weather_realtime_gold"
BQ_LOCATION = "europe-west1"
DEFAULT_LOCATION = "london"

COLUMNS = [
    "source_object", "event_time", "location_name", "location_lat", 
    "location_lon", "location_type", "ingested_at_utc", 
    "weather_temperature", "weather_humidity", "weather_windSpeed",
    "weather_cloudCover", "weather_precipitationProbability"
]

SCHEMA_FIELDS = [
    {"name": "source_object", "type": "STRING", "mode": "REQUIRED"},
    {"name": "event_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "location_name", "type": "STRING", "mode": "REQUIRED"},
    {"name": "location_lat", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "location_lon", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "location_type", "type": "STRING", "mode": "NULLABLE"},
    {"name": "ingested_at_utc", "type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "weather_temperature", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "weather_humidity", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "weather_windSpeed", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "weather_cloudCover", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "weather_precipitationProbability", "type": "FLOAT", "mode": "NULLABLE"},
]

RANGES = {
    "temperature": (-90, 70),
    "humidity": (0, 100),
    "windSpeed": (0, 150),
    "cloudCover": (0, 100),
    "precipitationProbability": (0, 100)
}

def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def flatten_and_validate(payload, source_object, ingested_at):
    """Return (row, None) if valid, or (None, reason) if not."""
    if not isinstance(payload, dict):
        return None, "payload is not an object"

    data, location = payload.get("data"), payload.get("location")
    if not isinstance(data, dict):
        return None, "data missing or not a dict"
    if not isinstance(location, dict):
        return None, "location missing or not a dict"
    values = data.get("values")
    if not isinstance(values, dict):
        return None, "data.values missing or not a dict"

    event_time = data.get("time")
    location_name = location.get("name")
    if not event_time or not location_name:
        return None, "missing time or location name"

    for field, (low, high) in RANGES.items():
        if field in values:
            v = values[field]
            if not is_number(v):
                return None, f"{field} is not numeric: {v!r}"
            if not low <= v <= high:
                return None, f"{field}={v} outside {low}..{high}"

    def num(d, key):
        v = d.get(key)
        return v if is_number(v) else None

    row = {
        "source_object": f"gs://{BRONZE_BUCKET}/{source_object}",
        "event_time": event_time,
        "location_name": location_name,
        "location_lat": num(location, "lat"),
        "location_lon": num(location, "lon"),
        "location_type": location.get("type"),
        "ingested_at_utc": ingested_at,
        "weather_temperature": values.get("temperature"),
        "weather_humidity": values.get("humidity"),
        "weather_windSpeed": values.get("windSpeed"),
        "weather_cloudCover": values.get("cloudCover"),
        "weather_precipitationProbability": values.get("precipitationProbability"),
    }

    return row, None

with DAG(
    dag_id="weather_silver_processing",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    params={
        "source_path": Param(
            None,
            type=["null", "string"],
            description="Optional bronze prefix, e.g. bronze/weather/realtime/london/2026/10/11/09/",
        ),
        "location": Param(DEFAULT_LOCATION, type="string"),
    },
    tags=["weather", "silver"],
) as dag:
    @task
    def build_silver(**context):
        params = context["params"]
        now = datetime.now(timezone.utc)

        source_path = params.get("source_path")
        if not source_path:
            prev = now - timedelta(hours=1)
            source_path = (
                f"bronze/weather/realtime/{params['location']}/{prev:%Y/%m/%d/%H}/"
            )

        if not source_path.endswith("/"):
            source_path += "/"

        if not source_path.startswith("bronze/"):
            raise ValueError("source_path must start with 'bronze/'")
        log.info("Processing prefix: gs://%s/%s", BRONZE_BUCKET, source_path)

        hook = GCSHook()
        objects = sorted(
            o for o in hook.list(BRONZE_BUCKET, prefix=source_path) if o.endswith(".json")
        )

        if not objects:
            raise ValueError(f"No .json files under gs://{BRONZE_BUCKET}/{source_path}")

        ingested_at = now.isoformat()
        rows, seen, rejected, duplicates = [], set(), 0, 0

        for obj in objects:
            try:
                payload = json.loads(hook.download(bucket_name=BRONZE_BUCKET, object_name=obj))
            except ValueError as exc:
                log.warning("Dropping %s: invalid JSON (%s)", obj, exc)
                rejected += 1
                continue

            row, reason = flatten_and_validate(payload, obj, ingested_at)
            if row is None:
                log.warning("Dropping %s: %s", obj, reason)
                rejected += 1
                continue

            key = (row["location_name"], row["event_time"])
            if key in seen:
                log.warning("Dropping %s: duplicate %s", obj, key)
                duplicates += 1
                continue

            seen.add(key)
            rows.append(row)

        log.info(
            "files=%d valid=%d rejected=%d duplicates=%d",
            len(objects), len(rows), rejected, duplicates,
        )

        if not rows:
            raise ValueError("No valid records after validation")

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

        silver_object = (
            "silver/" + source_path[len("bronze/"):] + f"{now:%Y%m%dT%H%M%SZ}.csv"
        )

        hook.upload(
            bucket_name = SILVER_BUCKET,
            object_name = silver_object,
            data = buffer.getvalue(),
            mime_type = "text/csv",
        )

        log.info("Wrote gs://%s/%s", SILVER_BUCKET, silver_object)
        return silver_object

    load_to_gold = GCSToBigQueryOperator(
        task_id="load_to_bigquery_gold",
        bucket=SILVER_BUCKET,
        source_objects=["{{ ti.xcom_pull(task_ids='build_silver') }}"],
        destination_project_dataset_table=BQ_TABLE,
        source_format="CSV",
        skip_leading_rows=1,
        schema_fields=SCHEMA_FIELDS,
        write_disposition="WRITE_APPEND",
        create_disposition="CREATE_NEVER",
        autodetect=False,
        location=BQ_LOCATION
    )


    build_silver_task = build_silver()
    build_silver_task >> load_to_gold
