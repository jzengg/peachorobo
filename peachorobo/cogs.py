import discord
from discord.ext import commands, tasks

from bot_utils import send_invitation, handle_invite_confirmed
from calendar_service import CalendarService
from constants import (
    MYSTERY_DINNER_CONFIRMATION_EMOJI,
    MYSTERY_DINNER_CANCEL_EMOJI,
)
from config import peachorobo_config
from db import DBService
from utils import parse_raw_datetime, get_pretty_datetime

intents = discord.Intents().default()
intents.members = True


def _prefix_callable(_bot, _msg):
    return peachorobo_config.bot_command_prefix


bot = commands.Bot(command_prefix=_prefix_callable, intents=intents)


async def on_command_error(ctx, error):
    await ctx.channel.send(error)


def check_if_mystery_dinner_channel(ctx):
    if ctx.channel.id != peachorobo_config.channel_id:
        raise commands.CheckFailure(
            message="Can only be used in the Mystery Dinner channel"
        )
    return True


class PreDinner(commands.Cog):
    """utilities that can be used before a mystery dinner is scheduled"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        await on_command_error(ctx, error)

    @commands.command(
        help="Schedule a mystery dinner using a date and time",
        usage="next friday at 6pm",
    )
    @commands.check(check_if_mystery_dinner_channel)
    async def schedule(self, ctx: commands.Context, *, raw_datetime: str):
        datetime_obj = parse_raw_datetime(raw_datetime)
        mystery_dinner_time = get_pretty_datetime(datetime_obj)
        await send_invitation(ctx, mystery_dinner_time)

        def is_invite_confirmed(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) == MYSTERY_DINNER_CONFIRMATION_EMOJI
            )

        await self.bot.wait_for("reaction_add", timeout=60.0, check=is_invite_confirmed)

        await handle_invite_confirmed(
            ctx,
            mystery_dinner_time,
            datetime_obj,
        )

    @commands.command(help="Get information about the next upcoming mystery dinner")
    @commands.check_any(
        commands.dm_only(), commands.check(check_if_mystery_dinner_channel)
    )
    async def remindme(self, ctx):
        next_dinner = DBService.get_latest_mystery_dinner(self.bot)
        if not next_dinner:
            raise commands.CommandError("No upcoming dinner")
        is_dm = ctx.channel.type == discord.ChannelType.private
        if is_dm:
            pairing = next(
                (
                    pairing
                    for pairing in next_dinner.pairings
                    if pairing.user.id == ctx.author.id
                ),
                None,
            )
            if not pairing:
                raise commands.CommandError("No pairing found")
            recipient = pairing.matched_with
            await ctx.author.send(
                f"The next dinner with id {next_dinner.id} will be {get_pretty_datetime(next_dinner.time)}. "
                f"The hangouts link is {next_dinner.calendar.get('uri')}. "
                f"You're getting dinner for {recipient.display_name}"
            )
        else:
            await ctx.channel.send(
                f"The next dinner with id {next_dinner.id} will be {get_pretty_datetime(next_dinner.time)}. "
                f"The hangouts link is {next_dinner.calendar.get('uri')}"
            )


class PostDinner(commands.Cog):
    """utilities after a mystery dinner has been scheduled"""

    def __init__(self, bot):
        self.bot = bot
        self.next_dinner = None

    async def cog_command_error(self, ctx, error):
        await on_command_error(ctx, error)

    async def cog_check(self, _ctx):
        next_dinner = DBService.get_latest_mystery_dinner(self.bot)
        self.next_dinner = next_dinner
        if not self.next_dinner:
            raise commands.CommandError(message="No upcoming dinners found")
        return True

    @commands.command(help="Cancels the next mystery dinner")
    @commands.check(check_if_mystery_dinner_channel)
    async def cancel(self, ctx):
        assert self.next_dinner is not None
        cancel_message = await ctx.channel.send(
            content=f"Are you sure you want to cancel the next dinner with id {self.next_dinner.id} on "
            f"{get_pretty_datetime(self.next_dinner.time)}. "
            f"React with {MYSTERY_DINNER_CANCEL_EMOJI} to confirm."
        )
        await cancel_message.add_reaction(MYSTERY_DINNER_CANCEL_EMOJI)

        def is_confirmed(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) == MYSTERY_DINNER_CANCEL_EMOJI
            )

        await self.bot.wait_for("reaction_add", timeout=60.0, check=is_confirmed)
        event_id = self.next_dinner.calendar.get("id")
        calendar_service = CalendarService()
        calendar_service.delete_event(event_id)
        DBService.cancel_latest_mystery_dinner()
        await ctx.channel.send(
            f"The next dinner with id {self.next_dinner.id} on {get_pretty_datetime(self.next_dinner.time)} "
            f"was cancelled @everyone"
        )

    @commands.command(
        help="Send an anonymous message to the person you're gifting",
        usage="your food is here!",
    )
    @commands.dm_only()
    async def yourfoodshere(self, ctx, *, message: str):
        assert self.next_dinner is not None
        author = ctx.author
        pairing = next(
            (
                pairing
                for pairing in self.next_dinner.pairings
                if pairing.user.id == author.id
            ),
            None,
        )
        if not pairing:
            raise commands.CommandError("No pairing found")
        matched_with_user = pairing.matched_with
        await matched_with_user.send(f"Your gifter says via Peacho: {message}")
        await ctx.author.send(
            f"Message successfully sent to recipient {matched_with_user.display_name}."
        )

    @commands.command(
        help="Send an anonymous message to your benefactor",
        usage="where's my food?",
    )
    @commands.dm_only()
    async def wheresmyfood(self, ctx, *, message: str):
        assert self.next_dinner is not None
        author = ctx.author
        pairing = next(
            (
                pairing
                for pairing in self.next_dinner.pairings
                if pairing.matched_with.id == author.id
            ),
            None,
        )
        if not pairing:
            raise commands.CommandError("No pairing found")
        gifter = pairing.user
        await gifter.send(f"Your recipient says via Peacho: {message}")
        await ctx.author.send(f"Message successfully sent to your gifter")


class WackWatch(commands.Cog):
    """utility to monitor wack logs"""

    def __init__(self, bot):
        self.bot = bot
        self.watch.start()

    def cog_unload(self):
        self.watch.cancel()

    @commands.command(
        help="Manually run wack watch",
    )
    async def wackwatch(self, ctx):
        await ctx.send("Manually running wack watch")
        message = await self.watch()
        await ctx.send(f"Finished wack watch: {message}")

    @tasks.loop(minutes=20.0)
    async def watch(self) -> str:
        errors = []
        log_path = peachorobo_config.wack_log_path
        try:
            with open(log_path) as f:
                for line in f:
                    if "WACK_ERROR" in line:
                        errors.append(line)
        except FileNotFoundError:
            open(log_path, "a").close()
        if errors:
            message = "wack error occurred"
            await self.bot.get_channel(peachorobo_config.debug_channel_id).send(
                f'wack error occurred {", ".join(errors)}'
            )
        else:
            message = "No errors found, clearing logs"
            open(log_path, "w").close()
        return message

    @watch.before_loop
    async def before_watch(self):
        print("waiting...")
        await self.bot.wait_until_ready()
