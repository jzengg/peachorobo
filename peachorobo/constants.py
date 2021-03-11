from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import discord
from typing_extensions import TypedDict

MYSTERY_DINNER_PICTURE_URI = "https://i.imgur.com/4ZKWUVC.jpg"
MYSTERY_DINNER_CONFIRMATION_EMOJI = "<:peach_hungry:819035345307566082>"
MYSTERY_DINNER_CANCEL_EMOJI = "<:mayu_nya:819042520288722964>"


@dataclass
class MysteryDinnerPairing:
    user: discord.User
    matched_with: discord.User


class MysteryDinnerCalendar(TypedDict):
    uri: Optional[str]
    id: str


@dataclass
class MysteryDinner:
    pairings: List[MysteryDinnerPairing]
    id: int
    time: datetime
    calendar: MysteryDinnerCalendar


class SerializedUser(TypedDict):
    display_name: str
    id: int
    name: str
    bot: bool


class SerializedPairing(TypedDict):
    user: SerializedUser
    matched_with: SerializedUser


class SerializedMysteryDinner(TypedDict):
    calendar: MysteryDinnerCalendar
    pairings: List[SerializedPairing]
    id: int
    datetime_iso: str
