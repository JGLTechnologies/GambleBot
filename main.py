import logging
import aiosqlite
import disnake
import os
from disnake.ext import commands
import time
from dotenv import load_dotenv
import db

load_dotenv()
logging.basicConfig(filename='GambleBot.log', level=logging.ERROR,
                    format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m-%d-%Y %I:%M:%S %p")
TOKEN = os.environ.get("GambleBot_TOKEN")
cogs = ["cogs.rps", "cogs.events", "cogs.commands", "cogs.credit", "cogs.shop", "cogs.blackjack", "cogs.drugs"]
bot = commands.AutoShardedInteractionBot(intents=disnake.Intents.all(), sync_commands_debug=True)


def load_cogs():
    for cog in cogs:
        bot.load_extension(cog)


def int_to_money(num: int) -> str:
    number_with_commas = "{:,}".format(round(num, 2))
    if "." in number_with_commas and int(number_with_commas.split(".")[1]) == 0:
        return "$" + number_with_commas.split(".")[0]
    return "$" + number_with_commas


def get_discord_date(ts: int = None) -> str:
    return f"<t:{int(ts or time.time())}:D>, <t:{int(ts or time.time())}:T> (<t:{int(ts or time.time())}:R>)"


async def start():
    db1 = await aiosqlite.connect("bot.db")
    db2 = await aiosqlite.connect("bot.db")
    await db.setup(db1)
    bot.db = db2

load_cogs()
bot.loop.create_task(start())
bot.run(TOKEN)
