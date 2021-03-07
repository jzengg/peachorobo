import json
from datetime import datetime
import pytz

JSON_PATH = "data/db.json"


def get_mystery_dinners():
    try:
        with open(JSON_PATH, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    return data


def create_mystery_dinner(pairings, scheduled_time):
    dinners = get_mystery_dinners()
    dinners.append({'pairings': pairings, 'datetime_iso': scheduled_time.isoformat(), 'id': len(dinners) + 1})
    with open(JSON_PATH, 'w') as f:
        json.dump(dinners, f)


def get_latest_mystery_dinner():
    dinners = get_mystery_dinners()
    if not dinners:
        return None
    last_dinner = dinners[-1]
    last_dinner_time = datetime.fromisoformat(last_dinner['datetime_iso'])
    utc_now = pytz.utc.localize(datetime.utcnow())
    est_now = utc_now.astimezone(pytz.timezone("US/Eastern"))
    if last_dinner_time < est_now:
        return None
    return {'pairings': last_dinner['pairings'], 'id': last_dinner['id'], 'time': last_dinner_time}
