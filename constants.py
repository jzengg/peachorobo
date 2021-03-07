import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing_extensions import TypedDict

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MYSTERY_DINNER_CHANNEL_ID = int(os.getenv("DISCORD_MYSTERY_DINNER_CHANNEL_ID"))
MYSTERY_DINNER_PICTURE_URI = "https://i.imgur.com/4ZKWUVC.jpg"
MYSTERY_DINNER_CONFIRMATION_EMOJI = "👍"

DiscordUser = discord.User
DiscordContext = commands.context
DiscordBot = commands.Bot


@dataclass
class MysteryDinnerPairing:
    user: DiscordUser
    matched_with: DiscordUser


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
