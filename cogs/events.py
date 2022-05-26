import contextlib
import logging
import time
from main import get_discord_date
import disnake
from disnake.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot

    @commands.Cog.listener("on_error")
    async def on_error(self, error):
        logging.error(error)

    @commands.Cog.listener("on_slash_command_error")
    async def slash_error(self, inter: disnake.MessageCommandInteraction, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.errors.CommandOnCooldown):
            time_remaining = round(error.retry_after, 2)
            time_remaining = time.time() + time_remaining
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(time_remaining)} to use that command again.",
                ephemeral=True)
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            pass
        elif isinstance(error, commands.errors.BotMissingPermissions) and not hasattr(inter, "handled_in_local"):
            missing_perms = ", ".join(error.missing_perms)
            msg = f"I am missing {missing_perms}."
            await inter.response.send_message(msg, ephemeral=True)
        elif isinstance(error, commands.errors.RoleNotFound):
            msg = f"Role not found: {error.argument}"
            await inter.response.send_message(msg, ephemeral=True)
        elif isinstance(error, commands.errors.ChannelNotFound):
            msg = f"Channel not found: {error.argument}"
            await inter.response.send_message(msg, ephemeral=True)
        elif isinstance(error, commands.errors.MemberNotFound) and not hasattr(inter,
                                                                               "handled_in_local"):
            msg = f"Member not found: {error.argument}"
            await inter.response.send_message(msg, ephemeral=True)
        elif isinstance(error, commands.errors.UserNotFound) and not hasattr(inter,
                                                                             "handled_in_local"):
            msg = f"User not found: {error.argument}"
            await inter.response.send_message(msg, ephemeral=True)
        elif isinstance(error, commands.errors.MissingPermissions) and not hasattr(inter,
                                                                                   "handled_in_local"):
            await inter.response.send_message("You do not have permission to do that.",
                                              ephemeral=True)
        elif isinstance(error, commands.errors.MissingRole) and not hasattr(inter,
                                                                            "handled_in_local"):
            await inter.response.send_message("You do not have permission to do that.",
                                              ephemeral=True)
        elif isinstance(error, disnake.ext.commands.errors.NoPrivateMessage):
            await inter.response.send_message("You cannot use this command in a private message.",
                                              ephemeral=True)
        elif isinstance(error, disnake.Forbidden):
            await inter.response.send_message("I don't have permission to do that.",
                                              ephemeral=True)
        else:
            if not hasattr(inter, "handled_in_local"):
                print(f"Error in {inter.application_command.name}")
                raise error

    @commands.Cog.listener("on_connect")
    async def on_ready(self):
        print("Bot is ready")

    @commands.Cog.listener("on_guild_join")
    async def message_guild_owner(self, guild: disnake.Guild):
        with contextlib.suppress(disnake.Forbidden, disnake.HTTPException):
            await guild.owner.send("Thank you for adding me to your server! Do `/commands` for a list of commands.")


def setup(bot):
    bot.add_cog(Events(bot))
