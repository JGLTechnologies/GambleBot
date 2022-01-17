import aiosqlite
import disnake
from disnake.ext import commands, tasks
import random
from db import get_business_stats, has_business, update_business_stats, get_balance, set_balance
from limits import RateLimitItemPerMinute
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter

from main import get_discord_date

minute_items = {}


def get_minute_item(minutes: int) -> RateLimitItemPerMinute:
    item = minute_items.get(minutes)
    if item is not None:
        return item
    item = RateLimitItemPerMinute(1, minutes)
    minute_items[minutes] = item
    return item


class Drugs(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot
        self.supplies_loop.start()
        self.storage = MemoryStorage()
        self.moving_window = MovingWindowRateLimiter(self.storage)

    @commands.slash_command(name="drugs")
    async def drugs(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @drugs.sub_command(name="steal")
    async def drugs_steal(self, inter: disnake.ApplicationCommandInteraction):
        if not await self.moving_window.test(get_minute_item(1),
                                             ["steal", inter.guild_id, inter.author.id]):
            reset_time, _ = await self.moving_window.get_window_stats(get_minute_item(15),
                                                                      ["steal", inter.guild_id,
                                                                       inter.author.id])
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        if not await has_business(inter.guild_id, inter.author.id, "drugs"):
            await inter.response.send_message(
                "You must have the drug distribution business to use that command. Buy it by doing `/buyitem drugs`",
                ephemeral=True)
            return
        await self.moving_window.hit(get_minute_item(1), ["steal", inter.guild_id, inter.author.id])
        supplies = random.randrange(9000, 15000)
        cops = random.randrange(0, 15) == 1
        if cops:
            await inter.response.send_message("You were caught by the cops and gained no supplies.")
            return
        await inter.response.send_message(f"You successfully stole ${supplies} worth of supplies.")
        p, s, u = await get_business_stats(inter.guild_id, inter.author.id, "drugs")
        await update_business_stats(inter.guild_id, inter.author.id, "drugs", product=p, supplies=s + supplies,
                                    upgraded=u)

    @drugs.sub_command(name="sell")
    async def drugs_sell(self, inter: disnake.ApplicationCommandInteraction):
        if not await self.moving_window.test(get_minute_item(20),
                                             ["sell", inter.guild_id, inter.author.id]):
            reset_time, _ = await self.moving_window.get_window_stats(get_minute_item(20),
                                                                      ["sell", inter.guild_id,
                                                                       inter.author.id])
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        if not await has_business(inter.guild_id, inter.author.id, "drugs"):
            await inter.response.send_message(
                "You must have the drug distribution business to use that command. Buy it by doing `/buyitem drugs`",
                ephemeral=True)
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        p, s, u = await get_business_stats(inter.guild_id, inter.author.id, "drugs")
        if p <= 0:
            await inter.response.send_message("You do not have anything to sell.", ephemeral=True)
            return
        await self.moving_window.hit(get_minute_item(20), ["sell", inter.guild_id, inter.author.id])
        await set_balance(inter.guild_id, inter.author.id, bal + p)
        await update_business_stats(inter.guild_id, inter.author.id, "drugs", product=0, supplies=s,
                                    upgraded=u)
        await inter.response.send_message(f"You successfully sold ${p} worth of drugs.")

    @drugs.sub_command(name="upgrade")
    async def drugs_upgrade(self, inter: disnake.ApplicationCommandInteraction):
        if not await has_business(inter.guild_id, inter.author.id, "drugs"):
            await inter.response.send_message(
                "You must have the drug distribution business to use that command. Buy it by doing `/buyitem drugs`",
                ephemeral=True)
            return
        p, s, u = await get_business_stats(inter.guild_id, inter.author.id, "drugs")
        if not bool(u):
            await inter.response.send_message("You drug distribution business is already upgraded.", ephemeral=True)
            return
        await update_business_stats(inter.guild_id, inter.author.id, "drugs", product=p, supplies=s,
                                    upgraded=1)
        await inter.response.send_message("You successfully upgraded your drug distribution business.")

    @drugs.sub_command(name="info")
    async def info(self, inter: disnake.ApplicationCommandInteraction):
        if not await has_business(inter.guild_id, inter.author.id, "drugs"):
            await inter.response.send_message(
                "You must have the drug distribution business to use that command. Buy it by doing `/buyitem drugs`",
                ephemeral=True)
            return
        p, s, u = await get_business_stats(inter.guild_id, inter.author.id, "drugs")
        u = bool(u)
        embed = disnake.Embed(title="Drug Distribution Business Info", color=disnake.Color.blurple())
        embed.add_field(name="Supplies", inline=False, value=f"${s}")
        embed.add_field(name="Product", inline=False, value=f"${p}")
        embed.add_field(name="Upgraded", inline=False, value=str(u))
        await inter.response.send_message(embed=embed)

    @tasks.loop(minutes=1)
    async def supplies_loop(self):
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("""CREATE TABLE IF NOT EXISTS business(
                member INTEGER,
                guild INTEGER,
                upgraded INTEGER,
                name TEXT,
                supplies INT,
                product INT,
                PRIMARY KEY (name, member, guild)
            )"""):
                pass
            await db.commit()
            async with db.execute("SELECT upgraded,supplies,member,guild,product FROM business WHERE name=?",
                                  ("drugs",)) as cursor:
                async for entry in cursor:
                    u, supplies, member, guild, product = entry
                    if supplies <= 0:
                        continue
                    if not bool(u):
                        if supplies < 5000:
                            product += supplies
                            supplies = 0
                        else:
                            product += 5000
                            supplies -= 5000
                    else:
                        if supplies < 10000:
                            product += supplies
                            supplies = 0
                        else:
                            product += 10000
                            supplies -= 10000
                    async with db.execute(
                            "UPDATE business SET product=?,supplies=?,upgraded=? WHERE guild=? and member=? and name=?",
                            (round(product, 2), round(supplies, 2), u, guild, member, "drugs")):
                        pass
                await db.commit()

    @supplies_loop.before_loop
    async def before_supplies_loop(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Drugs(bot))
