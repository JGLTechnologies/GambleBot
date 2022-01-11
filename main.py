import disnake
import os
from disnake.ext import commands
import aiosqlite
import sqlite3

TOKEN = os.environ.get("GambleBot_TOKEN")
cogs = ["cogs.rps", "cogs.events", "cogs.commands"]
bot = commands.AutoShardedInteractionBot(intents=disnake.Intents.all())


def load_cogs():
    for cog in cogs:
        bot.load_extension(cog)


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
        except sqlite3.IntegrityError:
            async with db.execute("UPDATE balances SET balance=? WHERE guild=? and member=?",
                                  (balance, guild_id, member_id)):
                pass
        finally:
            await db.commit()

load_cogs()
bot.run(TOKEN)
