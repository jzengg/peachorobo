import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from time import sleep

import aiohttp
import discord
from discord.ext import commands, tasks

from bot_utils import send_invitation, handle_invite_confirmed
from calendar_service import CalendarService
from constants import (
    MYSTERY_DINNER_CONFIRMATION_EMOJI,
    MYSTERY_DINNER_CANCEL_EMOJI,
    NBA_CONFIRMATION_EMOJI,
)
from config import peachorobo_config
from db import DBService
from nba import (
    get_most_recent_game_with_retry,
    get_team_id,
    get_player_id,
    get_video_data_with_retry,
    HighlightData,
)
from wack_utils import (
    get_live_num_sales,
    get_internal_num_sales,
    wack_has_been_run,
)
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
        # want to only send each alert once. need some kind of hash to tell us if we've sent that kind of alert before
        # and avoid sending it again
        self.messages_key = None

    def cog_unload(self):
        self.watch.cancel()

    @commands.command(
        help="Manually run wack watch",
    )
    async def wackwatch(self, ctx):
        await ctx.send("Manually running wack watch")
        await self.watch(ctx=ctx, verbose=True)
        await ctx.send(f"Finished wack watch")

    @tasks.loop(minutes=5.0)
    async def watch(self, ctx=None, verbose=False) -> None:
        messages = []
        channel = (
            ctx
            if ctx is not None
            else self.bot.get_channel(peachorobo_config.debug_channel_id)
        )
        try:
            did_run = wack_has_been_run()
            if did_run and verbose:
                messages.append("Wack ran in last 5 minutes")
            elif not did_run:
                messages.append("Wack has not run for more than 5 minutes. ERROR")
            retries = 12
            live_num_sales = await get_live_num_sales()
            while True:
                internal_num_sales = get_internal_num_sales()
                if live_num_sales != internal_num_sales:
                    if retries > 0:
                        retries -= 1
                        sleep(10)
                        continue
                    messages.append(
                        f"Wack error! {internal_num_sales} sales in Wack vs {live_num_sales} sales on etsy.com"
                    )
                    break
                else:
                    if verbose:
                        messages.append(
                            f"Number of sales in Wack ({internal_num_sales}) matches number of sales on etsy.com ({live_num_sales})"
                        )
                    break
        except Exception as e:
            messages.append(f"Error looking up last wack run: {e}")
        new_messages_key = hash(tuple(messages))
        if new_messages_key != self.messages_key:
            self.messages_key = new_messages_key
            for message in messages:
                await channel.send(message)

    @watch.before_loop
    async def before_watch(self):
        await self.bot.wait_until_ready()


class NBAHighlights(commands.Cog):
    """Get uri for nba highlights"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        help="Get highlights from the most recent NBA game",
        usage="DEN Nikola Jokic",
    )
    async def highlights(self, ctx, team_abbreviation: str, *, player_name: str):
        try:
            team_id = get_team_id(team_abbreviation.upper())
        except Exception as e:
            await ctx.send(f"Error getting team {e}")
            return
        try:
            player_id = get_player_id(player_name.title())
        except Exception as e:
            await ctx.send(f"Error getting player {e}")
            return

        await ctx.send(
            f"Getting the msot recent game {player_name} on {team_abbreviation}, please be patient..."
        )
        loop = asyncio.get_event_loop()
        most_recent_game_data = await loop.run_in_executor(
            ThreadPoolExecutor(), get_most_recent_game_with_retry, team_id, player_id
        )
        if most_recent_game_data is None:
            await ctx.send(
                f"Sorry, couldn't get the most recent game for {player_name}"
            )
            return

        game_description = (
            f"{most_recent_game_data.home_team} vs {most_recent_game_data.away_team} on "
            f"{most_recent_game_data.game_date.strftime('%A')} {most_recent_game_data.game_date}"
        )
        game_message = await ctx.send(
            f"Found a game: {game_description}. Show {len(most_recent_game_data.plays)} highlights now?"
        )
        await game_message.add_reaction(NBA_CONFIRMATION_EMOJI)

        def is_confirmed(reaction, user):
            return user == ctx.author and str(reaction.emoji) == NBA_CONFIRMATION_EMOJI

        await self.bot.wait_for("reaction_add", timeout=60.0, check=is_confirmed)

        for play_data in most_recent_game_data.plays:
            video_data = await get_video_data_with_retry(
                HighlightData(
                    game_id=most_recent_game_data.game_id, event_id=play_data.event_id
                )
            )
            if video_data is None:
                continue
            else:
                await ctx.send(f"{video_data.description}\n{video_data.uri}")


class CVSWatch(commands.Cog):
    """utility to check for vaccine appointments at CVS"""

    STATE_ABBREV = "MA"
    CVS_URL = f"http://www.cvs.com/immunizations/covid-19-vaccine.vaccine-status.{STATE_ABBREV}.json?vaccineinfo"
    HEADERS = {"Referer": "https://www.cvs.com/immunizations/covid-19-vaccine"}

    def __init__(self, bot):
        self.bot = bot
        self.cvswatch.start()

    @commands.command(
        help="Manually run appointment checker",
    )
    async def vacwatch(self, ctx):
        await ctx.send("Manually running vac watch")
        await self.cvswatch(ctx=ctx, verbose=True)
        await ctx.send(f"Finished vac watch")

    @tasks.loop(hours=1.0)
    async def cvswatch(self, ctx=None, verbose=False) -> None:
        messages = []
        channel = (
            ctx
            if ctx is not None
            else self.bot.get_channel(peachorobo_config.debug_channel_id)
        )
        try:
            openings = await self.get_openings()
            if openings:
                openings_message = ", ".join([opening["city"] for opening in openings])
                message = f"Openings available! book at: https://www.cvs.com/immunizations/covid-19-vaccine. Cities available: ${openings_message}"
                messages.append(message)
            elif not openings and verbose:
                messages.append("No openings found")
        except Exception as e:
            messages.append(f"Error checking appointments: {e}")

        for message in messages:
            await channel.send(message)

    @cvswatch.before_loop
    async def before_cvswatch(self):
        await self.bot.wait_until_ready()

    async def get_openings(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.CVS_URL, headers=self.HEADERS) as r:
                if r.status == 200:
                    json = await r.json()
                    data = json["responsePayloadData"]["data"][self.STATE_ABBREV]
                    openings = [city for city in data if city["status"] == "Available"]
                    return openings
