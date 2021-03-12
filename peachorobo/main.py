import argparse

from cogs import bot, PreDinner, PostDinner, WackWatch
from config import peachorobo_config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="peachorobo!!")
    parser.add_argument(
        "--dry",
        action="store_true",
        required=False,
        help="run as dry run",
    )
    args = parser.parse_args()
    peachorobo_config.load(not args.dry)
    bot.add_cog(PreDinner(bot))
    bot.add_cog(PostDinner(bot))
    bot.add_cog(WackWatch(bot))
    bot.run(peachorobo_config.discord_bot_token)
