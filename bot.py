import discord
from discord.ext import commands

from bot_utils import send_invitation, handle_invite_confirmed
from constants import MYSTERY_DINNER_CHANNEL_ID, MYSTERY_DINNER_CONFIRMATION_EMOJI
from db import get_latest_mystery_dinner, cancel_latest_mystery_dinner
from utils import parse_raw_datetime, get_pretty_datetime

intents = discord.Intents().default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send("Missing required argument: {}".format(error.param))
    else:
        await ctx.channel.send(error)


def check_if_mystery_dinner_channel(ctx):
    return ctx.channel.id == MYSTERY_DINNER_CHANNEL_ID


@bot.command(
    name="schedulemd",
    help="Schedule a mystery dinner using a date and time",
    usage="next friday at 6pm",
)
@commands.check(check_if_mystery_dinner_channel)
async def schedule_mystery_dinner(ctx, *, raw_datetime: str):
    datetime_obj = parse_raw_datetime(raw_datetime)
    mystery_dinner_time = get_pretty_datetime(datetime_obj)
    await send_invitation(ctx, mystery_dinner_time)

    def is_invite_confirmed(reaction, user):
        return (
            user == ctx.author
            and str(reaction.emoji) == MYSTERY_DINNER_CONFIRMATION_EMOJI
        )

    await bot.wait_for("reaction_add", timeout=60.0, check=is_invite_confirmed)

    await handle_invite_confirmed(ctx, mystery_dinner_time, datetime_obj)


@bot.command(
    name="nextmd", help="Get information about the next upcoming mystery dinner"
)
@commands.check(check_if_mystery_dinner_channel)
async def get_upcoming_mystery_dinner(ctx):
    next_dinner = get_latest_mystery_dinner(bot)
    if not next_dinner:
        await ctx.channel.send("No upcoming dinners found")
        return
    await ctx.channel.send(
        f"The next dinner with id {next_dinner.id} will be {get_pretty_datetime(next_dinner.time)}"
    )


@bot.command(name="cancelmd", help="Cancels the next mystery dinner")
@commands.check(check_if_mystery_dinner_channel)
async def cancel_upcoming_mystery_dinner(ctx):
    next_dinner = get_latest_mystery_dinner(bot)
    if not next_dinner:
        await ctx.channel.send("No upcoming dinners found")
        return

    cancel_message = await ctx.channel.send(
        content=f"Are you sure you want to cancel the next dinner with id {next_dinner.id} on "
        f"{get_pretty_datetime(next_dinner.time)}. "
        f"React with {MYSTERY_DINNER_CONFIRMATION_EMOJI} to confirm."
    )
    await cancel_message.add_reaction(MYSTERY_DINNER_CONFIRMATION_EMOJI)

    def is_confirmed(reaction, user):
        return (
            user == ctx.author
            and str(reaction.emoji) == MYSTERY_DINNER_CONFIRMATION_EMOJI
        )

    await bot.wait_for("reaction_add", timeout=60.0, check=is_confirmed)
    cancel_latest_mystery_dinner()
    await ctx.channel.send(
        f"The next dinner with id {next_dinner.id} on {get_pretty_datetime(next_dinner.time)} was cancelled"
    )


async def check_if_dm(ctx):
    is_dm = isinstance(ctx.channel, discord.DMChannel)
    return is_dm


@bot.command(
    name="yourfoodshere",
    help="Send an anonymous message to the person you're gifting",
    usage="your food is here!",
)
@commands.check(check_if_dm)
async def send_message_to_recipient(ctx, *, message: str):
    next_dinner = get_latest_mystery_dinner(bot)
    if not next_dinner:
        await ctx.channel.send("No upcoming dinners found")
        return
    author = ctx.author
    pairing = next(
        (pairing for pairing in next_dinner.pairings if pairing.user.id == author.id),
        None,
    )
    if not pairing:
        await ctx.channel.send("No pairings found")
        return
    matched_with_user = pairing.matched_with
    await matched_with_user.send(f"Your gifter says via Peacho: {message}")
    await ctx.author.send(
        f"Message successfully sent to recipient {matched_with_user.display_name}."
    )


@bot.command(
    name="wheresmyfood",
    help="Send an anonymous message to your benefactor",
    usage="where's my food?",
)
@commands.check(check_if_dm)
async def send_message_to_gifter(ctx, *, message: str):
    next_dinner = get_latest_mystery_dinner(bot)
    if not next_dinner:
        await ctx.channel.send("No upcoming dinners found")
        return
    author = ctx.author
    pairing = next(
        (
            pairing
            for pairing in next_dinner.pairings
            if pairing.matched_with.id == author.id
        ),
        None,
    )
    if not pairing:
        await ctx.channel.send("No pairings found")
        return
    gifter = pairing.user
    await gifter.send(f"Your recipient says via Peacho: {message}")
    await ctx.author.send(f"Message successfully sent to your gifter")
