import disnake
from disnake.ext import commands
from main import set_balance, get_balance


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="setbalance")
    @commands.has_permissions(administrator=True)
    async def set_balance(self, inter: disnake.MessageCommandInteraction, member: disnake.Member = commands.Param(),
                          balance: int = commands.Param()):
        await set_balance(inter.guild_id, member.id, balance)
        await inter.response.send_message(f"Set {str(member)}'s balance to ${balance}.", ephemeral=True)

    @commands.user_command(name="balance")
    async def set_balance(self, inter: disnake.MessageCommandInteraction, member: disnake.Member):
        bal = await get_balance(inter.guild_id, member.id)
        await inter.response.send_message(f"{str(member)}'s balance is ${bal}.")

    @commands.slash_command(name="ping")
    async def ping(self, inter: disnake.MessageCommandInteraction):
        await inter.response.send_message(f"Ping: {round(self.bot.latency, 2)}")


def setup(bot):
    bot.add_cog(Commands(bot))
