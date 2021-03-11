from datetime import datetime

import discord
import parsedatetime
from pytz import timezone

from constants import SerializedPairing, SerializedUser
from constants import MysteryDinnerPairing, MysteryDinner, SerializedMysteryDinner


def serialize_pairing(
    user: discord.User, matched_with: discord.User
) -> SerializedPairing:
    return {"user": serialize_user(user), "matched_with": serialize_user(matched_with)}


def serialize_user(user: discord.User) -> SerializedUser:
    return {
        "display_name": user.display_name,
        "id": user.id,
        "name": user.name,
        "bot": user.bot,
    }


def parse_raw_datetime(raw_datetime: str) -> datetime:
    cal = parsedatetime.Calendar()
    datetime_obj, status = cal.parseDT(
        datetimeString=raw_datetime, tzinfo=timezone("US/Eastern")
    )
    if status == 0:
        raise TypeError("Could not parse date and time")
    return datetime_obj


def get_pretty_datetime(datetime_obj: datetime) -> str:
    return datetime_obj.strftime("%A %B %d at %-I:%M %p")


def deserialize_mystery_dinner(dinner: SerializedMysteryDinner, bot) -> MysteryDinner:
    return MysteryDinner(
        id=dinner["id"],
        calendar=dinner["calendar"],
        time=datetime.fromisoformat(dinner["datetime_iso"]),
        pairings=[
            MysteryDinnerPairing(
                user=bot.get_user(pairing["user"]["id"]),
                matched_with=bot.get_user(pairing["matched_with"]["id"]),
            )
            for pairing in dinner["pairings"]
        ],
    )
