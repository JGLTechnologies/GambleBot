import time

import aiosqlite
import disnake
from disnake.ext import tasks, commands
from db import get_balance, add_security, set_balance, get_channel, remove_security


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot
        self.security_loop.start()

    @commands.slash_command(name="buyitem")
    @commands.guild_only()
    async def shop(self, inter: disnake.ApplicationCommandInteraction, item: str = commands.Param()):
        item = item.lower()
        items = ["security"]
        bal = await get_balance(inter.guild_id, inter.author.id)
        if bal <= 0:
            await inter.response.send_message("You do not have enough money.", ephemeral=True)
            return
        if item not in items:
            await inter.response.send_message("Invalid item", ephemeral=True)
            return
        if item == "security":
            if bal < 1000:
                await inter.response.send_message("You do not have enough money.", ephemeral=True)
                return
            await add_security(inter.guild_id, inter.author.id)
            await set_balance(inter.guild_id, inter.author.id, bal - 5000)
            await inter.response.send_message(
                f"You have successfully bought the security plan. Balance: ${round(bal - 5000, 2)}", ephemeral=True)

    @tasks.loop(seconds=10)
    async def security_loop(self):
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("""CREATE TABLE IF NOT EXISTS security(
                member INTEGER,
                guild INTEGER,
                last_paid INTEGER,
                PRIMARY KEY (member,guild)
            )"""):
                pass
            await db.commit()
            async with db.execute("SELECT member,guild,last_paid FROM security") as cursor:
                async for entry in cursor:
                    member_id, guild_id, last_paid = entry
                    if last_paid >= time.time() - 24 * 3600:
                        bal = await get_balance(guild_id, member_id)
                        guild = self.bot.get_guild(guild_id)
                        channel = guild.get_channel(await get_channel(guild_id, "bills"))
                        if bal - 5000 <= 0:
                            if channel is not None:
                                await channel.send(
                                    f"{guild.get_member(member_id).mention}, you do not have enough money to pay for security, so your subscription has been canceled.")
                            await remove_security(guild_id, member_id)
                        else:
                            await set_balance(guild_id, member_id, bal - 5000)
                            await channel.send(
                                f"{guild.get_member(member_id).mention}, you have been charged $5000 for your daily security bill.")

    @security_loop.before_loop
    async def before_security_loop(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Shop(bot))
