import json
from datetime import datetime
from typing import List, Optional

import pytz
from discord.ext import commands

from constants import (
    MysteryDinnerPairing,
    MysteryDinner,
    SerializedMysteryDinner,
    MysteryDinnerCalendar,
)
from utils import serialize_pairing, deserialize_mystery_dinner

JSON_PATH = "data/db.json"


def _get_serialized_mystery_dinners() -> List[SerializedMysteryDinner]:
    try:
        with open(JSON_PATH, "r") as f:
            serialized_dinners: List[SerializedMysteryDinner] = json.load(f)
    except FileNotFoundError:
        return []
    return serialized_dinners


def create_mystery_dinner(
    pairings: List[MysteryDinnerPairing],
    scheduled_time: datetime,
    calendar: MysteryDinnerCalendar,
) -> None:
    dinners = _get_serialized_mystery_dinners()
    serialized_pairings = [
        serialize_pairing(pairing.user, pairing.matched_with) for pairing in pairings
    ]
    serialized_dinner: SerializedMysteryDinner = {
        "pairings": serialized_pairings,
        "calendar": calendar,
        "datetime_iso": scheduled_time.isoformat(),
        "id": len(dinners) + 1,
    }
    dinners.append(serialized_dinner)
    with open(JSON_PATH, "w") as f:
        json.dump(dinners, f)


def get_latest_mystery_dinner(bot: commands.Bot) -> Optional[MysteryDinner]:
    dinners = _get_serialized_mystery_dinners()
    if not dinners:
        return None
    last_dinner = deserialize_mystery_dinner(dinners[-1], bot)
    utc_now = pytz.utc.localize(datetime.utcnow())
    est_now = utc_now.astimezone(pytz.timezone("US/Eastern"))
    if last_dinner.time < est_now:
        return None
    return last_dinner


def cancel_latest_mystery_dinner() -> None:
    dinners = _get_serialized_mystery_dinners()
    if not dinners:
        return
    dinners = dinners[:-1]
    with open(JSON_PATH, "w") as f:
        json.dump(dinners, f)
