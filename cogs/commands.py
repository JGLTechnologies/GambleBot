import disnake
from disnake.ext import commands
from main import set_balance, get_balance


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="setbalance")
    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def set_balance_command(self, inter: disnake.ApplicationCommandInteraction,
                                  member: disnake.Member = commands.Param(),
                                  balance: int = commands.Param()):
        await set_balance(inter.guild_id, member.id, balance)
        await inter.response.send_message(f"Set {str(member)}'s balance to ${balance}.", ephemeral=True)

    @commands.slash_command(name="balance")
    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    async def balance_command(self, inter: disnake.ApplicationCommandInteraction,
                              member: disnake.Member = commands.Param(default=None)):
        bal = await get_balance(inter.guild_id, member.id if member is not None else inter.author.id)
        await inter.response.send_message(f"{str(member or inter.author)}'s balance is ${bal}.")

    @commands.slash_command(name="ping")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(f"Ping: {round(self.bot.latency, 2)}ms")


def setup(bot):
    bot.add_cog(Commands(bot))
