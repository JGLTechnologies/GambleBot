import time
import disnake
from disnake.ext import tasks, commands
from main import int_to_money
from db import get_balance, add_security, set_balance, get_channel, remove_security, has_security, add_business, \
    has_business


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot
        self.security_loop.start()

    @commands.guild_only()
    @commands.slash_command(name="buyitem")
    async def buy_item(self, inter: disnake.ApplicationCommandInteraction, item: str = commands.Param()):
        item = item.lower()
        items = ["security", "drugs"]
        bal = await get_balance(inter.guild_id, inter.author.id)
        if bal <= 0:
            await inter.response.send_message("You do not have enough money.", ephemeral=True)
            return
        if item not in items:
            await inter.response.send_message("That item does not exist. Do `/shop` for a list of items.",
                                              ephemeral=True)
            return
        if item == "security":
            if await has_security(inter.guild_id, inter.author.id):
                await inter.response.send_message(
                    f"You already have the security plan.", ephemeral=True)
                return
            if bal < 1000:
                await inter.response.send_message("You do not have enough money.", ephemeral=True)
                return
            await add_security(inter.guild_id, inter.author.id)
            await set_balance(inter.guild_id, inter.author.id, bal - 100000)
            bal -= 100000
            await inter.response.send_message(
                f"You have successfully bought the security plan. Balance: {int_to_money(bal)}", ephemeral=True)
        elif item == "drugs":
            if await has_business(inter.guild_id, inter.author.id, "drugs"):
                await inter.response.send_message(
                    f"You already have the drug distribution business.", ephemeral=True)
                return
            if bal < 350000:
                await inter.response.send_message("You do not have enough money.", ephemeral=True)
                return
            await add_business(inter.guild_id, inter.author.id, "drugs")
            await set_balance(inter.guild_id, inter.author.id, bal - 350000)
            bal -= 350000
            await inter.response.send_message(
                f"You have successfully bought the drug distribution business. Balance: {int_to_money(bal)}",
                ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(name="unsubcribe")
    async def unsubscribe(self, inter: disnake.ApplicationCommandInteraction, item: str = commands.Param()):
        item = item.lower()
        items = ["security"]
        if item not in items:
            await inter.response.send_message(
                "That subscription does not exist. Do `/shop` for a list of subscriptions.",
                ephemeral=True)
            return
        if item == "security":
            if not await has_security(inter.guild_id, inter.author.id):
                await inter.response.send_message("You do not own security.",
                                                  ephemeral=True)
                return
            await remove_security(inter.guild_id, inter.author.id)
            await inter.response.send_message(
                f"You have successfully unsubscribed from the security plan.", ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(name="shop")
    async def shop(self, inter: disnake.ApplicationCommandInteraction):
        items = [{"name": "Security", "desc": "Lower you chances of getting robbed.", "type": "subscription",
                  "price": "$100,000 per day", "usage": "`/buyitem security`"},
                 {"name": "Drug Distribution Business", "desc": "Allows you to buy supplies to make and sell drugs.",
                  "type": "One Time Payment",
                  "price": "$350,000", "usage": "`/buyitem drugs`"}]
        embed = disnake.Embed(title=f"{inter.guild.name}'s Shop", color=disnake.Color.blurple())
        for item in items:
            embed.add_field(name=item["name"],
                            value=f"Description: {item['desc']}\nType: {item['type']}\nPrice: {item['price']}\nUsage: {item['usage']}",
                            inline=False)
        await inter.response.send_message(embed=embed)

    @tasks.loop(seconds=10)
    async def security_loop(self):
        async with self.bot.db.execute("""CREATE TABLE IF NOT EXISTS security(
                member INTEGER,
                guild INTEGER,
                last_paid INTEGER,
                PRIMARY KEY (member,guild)
            )"""):
            pass
        await self.bot.db.commit()
        async with self.bot.db.execute("SELECT member,guild,last_paid FROM security") as cursor:
            async for entry in cursor:
                member_id, guild_id, last_paid = entry
                if last_paid <= time.time() - (24 * 3600):
                    bal = await get_balance(guild_id, member_id)
                    guild = self.bot.get_guild(guild_id)
                    if guild is None:
                        continue
                    channel = guild.get_channel(await get_channel(guild_id, "bills"))
                    if bal - 100000 < 0:
                        if channel is not None:
                            await channel.send(
                                f"{guild.get_member(member_id).mention}, you do not have enough money to pay for security, so your subscription has been canceled.")
                        else:
                            try:
                                await guild.get_member(member_id).send(
                                    f"{guild.get_member(member_id).mention}, you do not have enough money to pay for security on {guild.name}, so your subscription has been canceled.")
                            except Exception:
                                continue
                        await remove_security(guild_id, member_id)
                    else:
                        await set_balance(guild_id, member_id, bal - 100000)
                        if channel is not None:
                            await channel.send(
                                f"{guild.get_member(member_id).mention}, you have been charged $100000 for your daily security bill.")
                        async with self.bot.db.execute("UPDATE security SET last_paid=? WHERE member=? and guild=?",
                                                       (time.time(), member_id, guild_id)):
                            pass
                        await self.bot.db.commit()

    @security_loop.before_loop
    async def before_security_loop(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Shop(bot))
