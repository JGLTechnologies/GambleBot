import disnake
import os
from disnake.ext import commands
import time
import logging

logging.basicConfig(filename='jglbot.log', encoding='utf-8', level=logging.ERROR,
                    format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m-%d-%Y %I:%M:%S %p")
TOKEN = os.environ.get("GambleBot_TOKEN")
cogs = ["cogs.rps", "cogs.events", "cogs.commands", "cogs.credit", "cogs.shop"]
bot = commands.AutoShardedInteractionBot(intents=disnake.Intents.all(), sync_commands_debug=True)


def load_cogs():
    for cog in cogs:
        bot.load_extension(cog)


def get_discord_date(ts: int = None) -> str:
    return f"<t:{int(ts or time.time())}:D>, <t:{int(ts or time.time())}:T> (<t:{int(ts or time.time())}:R>)"


load_cogs()
bot.run(TOKEN)
