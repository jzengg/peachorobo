import aiohttp

from discord.ext import commands, tasks

BOSTONIAN_CHANNEL_ID = 817411627682103336


class VacWatch(commands.Cog):
    """utility to check for vaccine appointments"""

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
        channel = ctx if ctx is not None else self.bot.get_channel(BOSTONIAN_CHANNEL_ID)
        try:
            openings = await self.get_cvs_openings()
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

    async def get_cvs_openings(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.CVS_URL, headers=self.HEADERS) as r:
                if r.status == 200:
                    json = await r.json()
                    data = json["responsePayloadData"]["data"][self.STATE_ABBREV]
                    openings = [city for city in data if city["status"] == "Available"]
                    return openings
