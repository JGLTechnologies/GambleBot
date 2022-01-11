import disnake
import os
from disnake.ext import commands
import time

TOKEN = os.environ.get("GambleBot_TOKEN")
cogs = ["cogs.rps", "cogs.events", "cogs.commands", "cogs.credit"]
bot = commands.AutoShardedInteractionBot(intents=disnake.Intents.all())


def load_cogs():
    for cog in cogs:
        bot.load_extension(cog)


def get_discord_date(ts: int = None) -> str:
    return f"<t:{int(ts or time.time())}> (<t:{int(ts or time.time())}:R>)"


load_cogs()
bot.run(TOKEN)
