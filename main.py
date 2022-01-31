import disnake
import os
from disnake.ext import commands
import time
import logging
from dotenv import load_dotenv


load_dotenv()
logging.basicConfig(filename='GambleBot.log', encoding='utf-8', level=logging.ERROR,
                    format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m-%d-%Y %I:%M:%S %p")
TOKEN = os.environ.get("GambleBot_TOKEN")
cogs = ["cogs.rps", "cogs.events", "cogs.commands", "cogs.credit", "cogs.shop", "cogs.blackjack", "cogs.drugs"]
bot = commands.AutoShardedInteractionBot(intents=disnake.Intents.all(), sync_commands_debug=True)


def int_to_money(num: int) -> str:
    number_with_commas = "{:,}".format(round(num, 2))
    return "$" + number_with_commas

def load_cogs():
    for cog in cogs:
        bot.load_extension(cog)


def get_discord_date(ts: int = None) -> str:
    return f"<t:{int(ts or time.time())}:D>, <t:{int(ts or time.time())}:T> (<t:{int(ts or time.time())}:R>)"


load_cogs()
bot.run(TOKEN)