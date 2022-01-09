import disnake
import os
import functools
from disnake.ext import commands
from typing import *
import aiosqlite

TOKEN = os.environ.get("GambleBot_TOKEN")
cogs = ["cogs.games", "cogs.events", "cogs.commands"]
bot = commands.AutoShardedInteractionBot(intents=disnake.Intents.all())


def load_cogs():
    for cog in cogs:
        bot.load_extension(cog)


class HasRoleCallable:
    def __init__(self, func) -> None:
        self.func = func

    def __call__(self, func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                if not isinstance(args[0], commands.Cog):
                    inter = args[0]
                else:
                    inter = args[1]
            except IndexError:
                inter = kwargs.get("inter")
            if role := inter.guild.get_role(await self.func(
                    inter)) not in inter.author.roles and not inter.author.guild_permissions.administrator:
                raise commands.errors.MissingRole(missing_role=role)
            return await func(*args, **kwargs)

        return wrapper


def has_role_callable(func: Awaitable) -> Any:
    return HasRoleCallable(func)


async def get_balance(guild_id: int, member_id: int):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS balances(
            guild INTEGER,
            member INTEGER,
            balance INTEGER,
            PRIMARY KEY (guild, member)
        )""")
        await db.commit()
        async with db.execute("SELECT balance FROM balances WHERE guild=? and member=?",
                              (guild_id, member_id)) as cursor:
            bal = await cursor.fetchone()
            if bal is not None:
                return bal[0]
            else:
                return 0


async def set_balance(guild_id: int, member_id: int, balance: int):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS balances(
            guild INTEGER,
            member INTEGER,
            balance INTEGER,
            PRIMARY KEY (guild, member)
        )""")
        await db.commit()
        try:
            async with db.execute("INSERT INTO balances (guild,member,balance) VALUES (?,?,?)",
                                  (guild_id, member_id, balance)):
                pass
        except:
            async with db.execute("UPDATE balances SET balance=? WHERE guild=? and member=?",
                                  (balance, guild_id, member_id)):
                pass


@bot.listen("on_ready")
async def on_ready():
    print("Bot is ready")


load_cogs()
bot.run(TOKEN)
