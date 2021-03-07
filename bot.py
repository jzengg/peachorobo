import copy
import os
import random

import discord
import parsedatetime
from dotenv import load_dotenv
from pytz import timezone

from db import create_mystery_dinner

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
MYSTERY_DINNER_CHANNEL_ID = int(os.getenv('DISCORD_MYSTERY_DINNER_CHANNEL_ID'))
MYSTERY_DINNER_PICTURE_URI = 'https://i.imgur.com/4ZKWUVC.jpg'
MYSTERY_DINNER_CONFIRMATION_EMOJI = '👍'


def make_pairings(members):
    temp_members = copy.copy(members)
    pairings = []
    random.shuffle(temp_members)
    for i in range(len(temp_members)):
        match = temp_members[i + 1] if i + 1 < len(temp_members) else temp_members[0]
        pairings.append({'user': temp_members[i], 'matched_with': match})
    return pairings


def serialize_pairing(user, recipient):
    return {'user': serialize_user(user), 'matched_with': serialize_user(recipient)}


def serialize_user(user):
    return {'display_name': user.display_name, 'id': user.id, 'name': user.name, 'bot': user.bot}


def parse_raw_datetime(raw_datetime):
    cal = parsedatetime.Calendar()
    datetime_obj, status = cal.parseDT(datetimeString=raw_datetime, tzinfo=timezone("US/Eastern"))
    if status == 0:
        raise TypeError('Could not parse date and time')
    return datetime_obj


def get_pretty_datetime(datetime_obj):
    return datetime_obj.strftime("%A %B %d at %-I:%M %p")


async def send_pairings_out(pairings, mystery_dinner_time):
    for pairing in pairings:
        giver = pairing['user']
        recipient = pairing['matched_with']
        await giver.send(
            f"Hi {giver.display_name}, you're getting dinner for {recipient.display_name}. "
            f"This is happening {mystery_dinner_time}. Use !help to see how to send anonymous messages")


async def send_invitation(channel, mystery_dinner_time):
    invitation_message = await channel.send(
        content=f"You want to schedule a mystery dinner for {mystery_dinner_time}? React with "
                f"{MYSTERY_DINNER_CONFIRMATION_EMOJI} to confirm and send out pairings.")
    await invitation_message.add_reaction(MYSTERY_DINNER_CONFIRMATION_EMOJI)


async def handle_invite_confirmed(ctx, mystery_dinner_time, datetime_obj):
    members = [member for member in ctx.channel.members if not member.bot]
    pairings = make_pairings(members)
    create_mystery_dinner([serialize_pairing(pairing['user'], pairing['matched_with']) for pairing in pairings],
                          datetime_obj)
    await send_pairings_out(pairings, mystery_dinner_time)
    mystery_dinner_embed = discord.Embed.from_dict({'image': {'url': MYSTERY_DINNER_PICTURE_URI}})
    await ctx.channel.send(content=f"That's it folks, all the pairings have been sent out. Enjoy your meal!",
                           embed=mystery_dinner_embed)
