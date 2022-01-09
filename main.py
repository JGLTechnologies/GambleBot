import disnake
import os
import functools
from disnake.ext import commands
from typing import *

TOKEN = os.environ.get("GambleBot_TOKEN")
cogs = ["cogs.games", "cogs.events"]
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


@bot.listen("on_ready")
async def on_ready():
    print("Bot is ready")


@bot.slash_command("ping")
async def ping(inter: disnake.MessageCommandInteraction):
    await inter.response.send_message(f"Ping: {round(bot.latency, 2)}")


load_cogs()
bot.run(TOKEN)
