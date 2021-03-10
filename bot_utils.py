import copy
import random
from datetime import datetime
from time import sleep
from typing import List, Optional

import discord
from discord.ext import commands

from calendar_service import CalendarService
from constants import (
    MYSTERY_DINNER_CONFIRMATION_EMOJI,
    MYSTERY_DINNER_PICTURE_URI,
    MysteryDinnerPairing,
    MysteryDinnerCalendar,
)
from db import create_mystery_dinner


def make_pairings(members: List[discord.User]) -> List[MysteryDinnerPairing]:
    temp_members = copy.copy(members)
    pairings = []
    random.shuffle(temp_members)
    for i in range(len(temp_members)):
        match = temp_members[i + 1] if i + 1 < len(temp_members) else temp_members[0]
        pairing = MysteryDinnerPairing(user=temp_members[i], matched_with=match)
        pairings.append(pairing)
    return pairings


async def send_pairings_out(
    pairings: List[MysteryDinnerPairing], mystery_dinner_time: str
) -> None:
    for pairing in pairings:
        giver = pairing.user
        recipient = pairing.matched_with
        await giver.send(
            f"Hi {giver.display_name}, you're getting dinner for {recipient.display_name}. "
            f"This is happening {mystery_dinner_time}. Use !help to see how to send anonymous messages"
        )


async def send_invitation(ctx: commands.Context, mystery_dinner_time: str) -> None:
    invitation_message = await ctx.channel.send(
        content=f"You want to schedule a mystery dinner for {mystery_dinner_time}? React with "
        f"{MYSTERY_DINNER_CONFIRMATION_EMOJI} to confirm and send out pairings."
    )
    await invitation_message.add_reaction(MYSTERY_DINNER_CONFIRMATION_EMOJI)


async def handle_invite_confirmed(
    ctx: commands.Context, mystery_dinner_time: str, datetime_obj: datetime
) -> None:
    members = [member for member in ctx.channel.members if not member.bot]
    pairings = make_pairings(members)
    calendar_service = CalendarService()
    event = calendar_service.create_event(datetime_obj)
    try:
        event_uri = event.conference_solution.entry_points[0].uri
    except Exception as e:
        event_uri = None

    calendar_data: MysteryDinnerCalendar = {"id": event.id, "uri": event_uri}
    create_mystery_dinner(pairings, datetime_obj, calendar_data)
    await send_pairings_out(pairings, mystery_dinner_time)

    mystery_dinner_embed = discord.Embed.from_dict(
        {"image": {"url": MYSTERY_DINNER_PICTURE_URI}}
    )
    await ctx.channel.send(
        content=f"That's it folks, all the pairings have been sent out. The hangout link is {event_uri}."
        f" Enjoy your meal!",
        embed=mystery_dinner_embed,
    )
