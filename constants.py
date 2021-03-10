import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

import discord
from dotenv import load_dotenv
from typing_extensions import TypedDict

load_dotenv()
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
MYSTERY_DINNER_CHANNEL_ID = int(os.environ["DISCORD_MYSTERY_DINNER_CHANNEL_ID"])
DISCORD_DEBUG_CHANNEL_ID = int(os.environ["DISCORD_DEBUG_CHANNEL_ID"])
MYSTERY_DINNER_PICTURE_URI = "https://i.imgur.com/4ZKWUVC.jpg"
MYSTERY_DINNER_CONFIRMATION_EMOJI = "👍"


@dataclass
class MysteryDinnerPairing:
    user: discord.User
    matched_with: discord.User


@dataclass
class MysteryDinner:
    pairings: List[MysteryDinnerPairing]
    id: int
    time: datetime


class SerializedUser(TypedDict):
    display_name: str
    id: int
    name: str
    bot: bool


class SerializedPairing(TypedDict):
    user: SerializedUser
    matched_with: SerializedUser


class SerializedMysteryDinner(TypedDict):
    pairings: List[SerializedPairing]
    id: int
    datetime_iso: str
