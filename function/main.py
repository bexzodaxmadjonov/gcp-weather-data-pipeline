import json 
import os
import re 
from datetime import datetime, timezone

import functions_framework
import requests 
from google.cloud import storage

API_URL = "https://api.tomorrow.io/v4/weather/realtime"
BUCKET = os.environ["BUCKET_NAME"]
API_KEY = os.environ["WEATHER_API_KEY"]
LOCATIONS = [l.strip() for l in os.environ["LOCATIONS"].split(",") if l.strip()]

client = storage.Client()

def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

@functions_framework.http 
def ingest(request): 
    now = datetime.now(timezone.utc)
    written, errors = [], []

    for loc in LOCATIONS:
        try: 
            resp = requests.get(
                API_URL,
                params={"location": loc, "apikey": API_KEY},
                timeout = 20,
            )
            resp.raise_for_status()
            path = (
                f"bronze/weather/realtime/{slug(loc)}/"
                f"{now:%Y/%m/%d/%H}/{now:%Y%m%dT%H%M%SZ}.json"
            )

            client.bucket(BUCKET).blob(path).upload_from_string(
                resp.text, content_type="application/json"
            )
            written.append(path)
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            print(f"ERROR location={loc} type={type(exc).__name__} status={status}")
            errors.append(loc)

    body = json.dumps({"written": written, "failed_locations": errors})
    return body, (500 if errors else 200), {"Content-Type": "application/json"}

