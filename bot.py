import copy
import os
import random

import discord
import parsedatetime
from discord.ext import commands
from dotenv import load_dotenv
from pytz import timezone

from db import create_mystery_dinner, get_latest_mystery_dinner, cancel_latest_mystery_dinner

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MYSTERY_DINNER_CHANNEL_ID = int(os.getenv('DISCORD_MYSTERY_DINNER_CHANNEL_ID'))
MYSTERY_DINNER_PICTURE_URI = 'https://i.imgur.com/4ZKWUVC.jpg'
MYSTERY_DINNER_CONFIRMATION_EMOJI = '👍'
intents = discord.Intents().default()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)


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


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send("Missing required argument: {}".format(error.param))
    else:
        await ctx.channel.send(error)


def check_if_mystery_dinner_channel(ctx):
    return ctx.channel.id == MYSTERY_DINNER_CHANNEL_ID


@bot.command(name="schedulemd", help="Schedule a mystery dinner using a date and time",
             usage="next friday at 6pm")
@commands.check(check_if_mystery_dinner_channel)
async def schedule_mystery_dinner(ctx, *, raw_datetime: str):
    datetime_obj = parse_raw_datetime(raw_datetime)
    mystery_dinner_time = get_pretty_datetime(datetime_obj)
    await send_invitation(ctx.channel, mystery_dinner_time)

    def is_invite_confirmed(reaction, user):
        return user == ctx.author and str(reaction.emoji) == MYSTERY_DINNER_CONFIRMATION_EMOJI

    await bot.wait_for('reaction_add', timeout=60.0, check=is_invite_confirmed)

    await handle_invite_confirmed(ctx, mystery_dinner_time, datetime_obj)


async def check_if_dm(ctx):
    is_dm = isinstance(ctx.channel, discord.DMChannel)
    return is_dm


@bot.command(name="nextmd", help="Get information about the next upcoming mystery dinner")
@commands.check(check_if_mystery_dinner_channel)
async def get_upcoming_mystery_dinner(ctx):
    next_dinner = get_latest_mystery_dinner()
    if not next_dinner:
        await ctx.channel.send('No upcoming dinners found')
        return
    await ctx.channel.send(
        f"The next dinner with id {next_dinner['id']} will be {get_pretty_datetime(next_dinner['time'])}")


@bot.command(name="cancelmd", help="Cancels the next mystery dinner")
@commands.check(check_if_mystery_dinner_channel)
async def cancel_upcoming_mystery_dinner(ctx):
    next_dinner = get_latest_mystery_dinner()
    if not next_dinner:
        await ctx.channel.send('No upcoming dinners found')
        return

    cancel_message = await ctx.channel.send(
        content=f"Are you sure you want to cancel the next dinner with id {next_dinner['id']} on {get_pretty_datetime(next_dinner['time'])}. "
                f"React with {MYSTERY_DINNER_CONFIRMATION_EMOJI} to confirm.")
    await cancel_message.add_reaction(MYSTERY_DINNER_CONFIRMATION_EMOJI)

    def is_confirmed(reaction, user):
        return user == ctx.author and str(reaction.emoji) == MYSTERY_DINNER_CONFIRMATION_EMOJI

    await bot.wait_for('reaction_add', timeout=60.0, check=is_confirmed)
    cancel_latest_mystery_dinner()
    await ctx.channel.send(
        f"The next dinner with id {next_dinner['id']} on {get_pretty_datetime(next_dinner['time'])} was cancelled")


@bot.command(name="yourfoodshere", help="Send an anonymous message to the person you're gifting",
             usage="your food is here!")
@commands.check(check_if_dm)
async def send_message_as_deliverer(ctx, *, message: str):
    next_dinner = get_latest_mystery_dinner()
    if not next_dinner:
        await ctx.channel.send('No upcoming dinners found')
        return
    author = ctx.author
    pairing = next((pairing for pairing in next_dinner['pairings'] if
                    pairing['user']['id'] == author.id), None)
    if not pairing:
        await ctx.channel.send('No pairings found')
        return
    matched_with_user = bot.get_user(pairing['matched_with']['id'])
    await matched_with_user.send(f'Private message delivered using Peacho: {message}')
    await ctx.author.send(f'Message successfully sent to recipient {matched_with_user.display_name}.')


@bot.command(name="wheresmyfood", help="Send an anonymous message to your benefactor",
             usage="where's my food?")
@commands.check(check_if_dm)
async def send_message_as_deliverer(ctx, *, message: str):
    next_dinner = get_latest_mystery_dinner()
    if not next_dinner:
        await ctx.channel.send('No upcoming dinners found')
        return
    author = ctx.author
    pairing = next((pairing for pairing in next_dinner['pairings'] if
                    pairing['matched_with']['id'] == author.id), None)
    if not pairing:
        await ctx.channel.send('No pairings found')
        return
    gifter = bot.get_user(pairing['user']['id'])
    await gifter.send(f'Private message delivered using Peacho: {message}')
    await ctx.author.send(f'Message successfully sent to your gifter')


bot.run(TOKEN)
