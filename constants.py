import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import discord
from dotenv import load_dotenv
from typing_extensions import TypedDict

load_dotenv()
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DEBUG_DISCORD_TOKEN = os.environ["DEBUG_DISCORD_TOKEN"]
DEBUG_CALENDAR_EMAILS = ["jzengg@gmail.com"]
CALENDAR_EMAILS = os.environ["CALENDAR_EMAILS"].split(",")
MYSTERY_DINNER_CHANNEL_ID = int(os.environ["DISCORD_MYSTERY_DINNER_CHANNEL_ID"])
MYSTERY_DINNER_DEBUG_CHANNEL_ID = int(
    os.environ["DISCORD_MYSTERY_DINNER_DEBUG_CHANNEL_ID"]
)
MYSTERY_DINNER_PICTURE_URI = "https://i.imgur.com/4ZKWUVC.jpg"
MYSTERY_DINNER_CONFIRMATION_EMOJI = "<:peach_hungry:819035345307566082>"
MYSTERY_DINNER_CANCEL_EMOJI = "<:mayu_nya:819042520288722964>"
JSON_PATH = "data/db.json"
DEBUG_JSON_PATH = "data/debug_db.json"


@dataclass
class PeachoroboConfig:
    channel_id: int = 0
    discord_bot_token: str = ""
    calendar_emails: List[str] = field(default_factory=list)
    db_json_path: str = ""

    def load(self, is_prod: bool) -> None:
        self.channel_id = (
            MYSTERY_DINNER_CHANNEL_ID if is_prod else MYSTERY_DINNER_DEBUG_CHANNEL_ID
        )
        self.discord_bot_token = DISCORD_TOKEN if is_prod else DEBUG_DISCORD_TOKEN
        self.calendar_emails = CALENDAR_EMAILS if is_prod else DEBUG_CALENDAR_EMAILS
        self.db_json_path = JSON_PATH if is_prod else DEBUG_JSON_PATH


peachorobo_config = PeachoroboConfig()


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
