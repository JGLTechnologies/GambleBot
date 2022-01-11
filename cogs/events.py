import disnake
from disnake.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot

    @commands.Cog.listener("on_slash_command_error")
    async def slash_error(self, inter: disnake.MessageCommandInteraction, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.errors.CommandOnCooldown):
            time_remaining = round(error.retry_after, 2)
            await inter.response.send_message(f"You need to wait {time_remaining} more seconds to use that again.",
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
        else:
            if not hasattr(inter, "handled_in_local"):
                print(f"Error in {inter.application_command.name}")
                raise error

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        print("Bot is ready")


def setup(bot):
    bot.add_cog(Events(bot))
