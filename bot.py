import copy
import os
import random

import discord
import parsedatetime
from discord.ext import commands
from dotenv import load_dotenv
from pytz import timezone

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MYSTERY_DINNER_CHANNEL_ID = 817422144739868674
MYSTERY_DINNER_PICTURE_URI = 'https://i.imgur.com/4ZKWUVC.jpg'
MYSTERY_DINNER_CONFIRMATION_EMOJI = '👍'
intents = discord.Intents().default()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)


def check_if_mystery_dinner_channel(ctx):
    return ctx.channel.id == MYSTERY_DINNER_CHANNEL_ID


def make_pairings(members):
    temp_members = copy.copy(members)
    pairings = []
    random.shuffle(temp_members)
    for i in range(len(temp_members)):
        match = temp_members[i + 1] if i + 1 < len(temp_members) else temp_members[0]
        pairings.append({'user': temp_members[i], 'matched_with': match})
    return pairings


def parse_raw_datetime(raw_datetime):
    cal = parsedatetime.Calendar()
    datetime_obj, status = cal.parseDT(datetimeString=raw_datetime, tzinfo=timezone("US/Eastern"))
    if status == 0:
        raise TypeError('Could not parse date and time')
    return datetime_obj.strftime("%A %B %d at %-I:%M %p")


async def send_pairings_out(members, mystery_dinner_time):
    pairings = make_pairings(members)
    for pairing in pairings:
        giver = pairing['user']
        recipient = pairing['matched_with']
        await giver.send(f"Hi {giver.display_name}, you're getting dinner for {recipient.display_name}. "
                         f"This is happening {mystery_dinner_time}")


async def send_invitation(channel, mystery_dinner_time):
    invitation_message = await channel.send(
        content=f"You want to schedule a mystery dinner for {mystery_dinner_time}? React with "
                f"{MYSTERY_DINNER_CONFIRMATION_EMOJI} to confirm and send out pairings.")
    await invitation_message.add_reaction(MYSTERY_DINNER_CONFIRMATION_EMOJI)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send("Missing required argument: {}".format(error.param))
    else:
        await ctx.channel.send(error)


@bot.command(name="schedulemd", help="Schedule a mystery dinner using a date and time",
             usage="next friday at 6pm")
@commands.check(check_if_mystery_dinner_channel)
async def scheduled_mystery_dinner(ctx, *, raw_datetime: str):
    mystery_dinner_time = parse_raw_datetime(raw_datetime)
    await send_invitation(ctx.channel, mystery_dinner_time)

    def is_invite_confirmed(reaction, user):
        return user == ctx.author and str(reaction.emoji) == MYSTERY_DINNER_CONFIRMATION_EMOJI
    await bot.wait_for('reaction_add', timeout=60.0, check=is_invite_confirmed)

    members = [member for member in ctx.channel.members if not member.bot]
    await send_pairings_out(members, mystery_dinner_time)
    mystery_dinner_embed = discord.Embed.from_dict({'image': {'url': MYSTERY_DINNER_PICTURE_URI}})
    await ctx.channel.send(content=f"That's it folks, all the pairings have been sent out. Enjoy your meal!",
                           embed=mystery_dinner_embed)


bot.run(TOKEN)
