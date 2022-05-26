import contextlib
import disnake
from disnake.ext import commands, tasks
import random
from db import get_business_stats, has_business, update_business_stats, get_balance, set_balance
from limits import RateLimitItemPerMinute
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter
from db import get_channel
from main import get_discord_date, int_to_money

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
        self.cops_loop.start()
        self.storage = MemoryStorage()
        self.moving_window = MovingWindowRateLimiter(self.storage)

    @commands.guild_only()
    @commands.slash_command(name="drugs")
    async def drugs(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @drugs.sub_command(name="steal")
    @commands.guild_only()
    async def drugs_steal(self, inter: disnake.ApplicationCommandInteraction):
        if not await self.moving_window.test(get_minute_item(5),
                                             "steal", inter.guild_id, inter.author.id):
            reset_time, _ = await self.moving_window.get_window_stats(get_minute_item(5),
                                                                      "steal", inter.guild_id,
                                                                      inter.author.id)
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        channel = await get_channel(inter.guild_id, "info")
        if channel is None:
            await inter.response.send_message(
                "An info channel has not been set for this server. Set one by doing /setchannel info #channel",
                ephemeral=True)
            return
        if not await has_business(inter.guild_id, inter.author.id, "drugs"):
            await inter.response.send_message(
                "You must have the drug distribution business to use that command. Buy it by doing `/buyitem drugs`",
                ephemeral=True)
            return
        await self.moving_window.hit(get_minute_item(5), "steal", inter.guild_id, inter.author.id)
        p, s, u = await get_business_stats(inter.guild_id, inter.author.id, "drugs")
        if s >= 1000:
            if not u:
                cartel = random.randrange(0, 15) == 1
            else:
                cartel = random.randrange(0, 25) == 1
            if cartel:
                await inter.response.send_message(
                    "You were caught by the Mexican Cartel, and they took 20% of your supplies.")
                await update_business_stats(inter.guild_id, inter.author.id, "drugs", product=p, supplies=s * .2,
                                            upgraded=u)
                return
        supplies = random.randrange(9000, 15000)
        if not u:
            cops = random.randrange(0, 15) == 1
        else:
            cops = random.randrange(0, 25) == 1
        if cops:
            await inter.response.send_message("You were caught by the cops and gained no supplies.")
            return
        await inter.response.send_message(f"You successfully stole ${supplies} worth of supplies.")
        await update_business_stats(inter.guild_id, inter.author.id, "drugs", product=p, supplies=s + supplies,
                                    upgraded=u)

    @drugs.sub_command(name="sell")
    @commands.guild_only()
    async def drugs_sell(self, inter: disnake.ApplicationCommandInteraction):
        if not await self.moving_window.test(get_minute_item(20),
                                             "sell", inter.guild_id, inter.author.id):
            reset_time, _ = await self.moving_window.get_window_stats(get_minute_item(20),
                                                                      "sell", inter.guild_id,
                                                                       inter.author.id)
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        channel = await get_channel(inter.guild_id, "info")
        if channel is None:
            await inter.response.send_message(
                "An info channel has not been set for this server. Set one by doing /setchannel info #channel",
                ephemeral=True)
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
        await self.moving_window.hit(get_minute_item(20), "sell", inter.guild_id, inter.author.id)
        await set_balance(inter.guild_id, inter.author.id, bal + p)
        await update_business_stats(inter.guild_id, inter.author.id, "drugs", product=0, supplies=s,
                                    upgraded=u)
        await inter.response.send_message(f"You successfully sold ${p} worth of drugs.")

    @drugs.sub_command(name="upgrade")
    @commands.guild_only()
    async def drugs_upgrade(self, inter: disnake.ApplicationCommandInteraction):
        if not await has_business(inter.guild_id, inter.author.id, "drugs"):
            await inter.response.send_message(
                "You must have the drug distribution business to use that command. Buy it by doing `/buyitem drugs`",
                ephemeral=True)
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        if bal < 200000:
            await inter.response.send_message("You have to have at least $200,000 to upgrade this business.",
                                              ephemeral=True)
            return
        p, s, u = await get_business_stats(inter.guild_id, inter.author.id, "drugs")
        if bool(u):
            await inter.response.send_message("Your drug distribution business is already upgraded.", ephemeral=True)
            return
        await update_business_stats(inter.guild_id, inter.author.id, "drugs", product=p, supplies=s,
                                    upgraded=1)
        bal -= 200000
        await inter.response.send_message(
            f"You successfully upgraded your drug distribution business. You now have {int_to_money(bal)}")
        await set_balance(inter.guild_id, inter.author.id, bal - 200000)

    @drugs.sub_command(name="info")
    @commands.guild_only()
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
        async with self.bot.db.execute("""CREATE TABLE IF NOT EXISTS business(
            member INTEGER,
            guild INTEGER,
            upgraded INTEGER,
            name TEXT,
            supplies INT,
            product INT,
            PRIMARY KEY (name, member, guild)
        )"""):
            pass
        await self.bot.db.commit()
        async with self.bot.db.execute("SELECT upgraded,supplies,member,guild,product FROM business WHERE name=?",
                                       ("drugs",)) as cursor:
            async for entry in cursor:
                u, supplies, member, guild, product = entry
                if supplies <= 0:
                    continue
                if self.bot.get_guild(guild) is None:
                    continue
                if self.bot.get_guild(guild).get_member(member) is None:
                    continue
                if str(self.bot.get_guild(guild).get_member(member).status) != "online":
                    continue
                if not bool(u):
                    if supplies < 2500:
                        product += supplies
                        supplies = 0
                    else:
                        product += 2500
                        supplies -= 2500
                else:
                    if supplies < 5000:
                        product += supplies
                        supplies = 0
                    else:
                        product += 5000
                        supplies -= 5000
                async with self.bot.db.execute(
                        "UPDATE business SET product=?,supplies=?,upgraded=? WHERE guild=? and member=? and name=?",
                        (round(product, 2), round(supplies, 2), u, guild, member, "drugs")):
                    pass
            await self.bot.db.commit()

    @tasks.loop(hours=24)
    async def cops_loop(self):
        async with self.bot.db.execute("""CREATE TABLE IF NOT EXISTS business(
                member INTEGER,
                guild INTEGER,
                upgraded INTEGER,
                name TEXT,
                supplies INT,
                product INT,
                PRIMARY KEY (name, member, guild)
            )"""):
            pass
        await self.bot.db.commit()
        async with self.bot.db.execute("SELECT upgraded,supplies,member,guild,product FROM business WHERE name=?",
                                       ("drugs",)) as cursor:
            async for entry in cursor:
                u, supplies, member, guild, product = entry
                if product <= 1000:
                    continue
                if not bool(u):
                    busted = random.randrange(0, 25) == 1
                else:
                    continue
                if busted:
                    async with self.bot.db.execute(
                            "UPDATE business SET product=? WHERE guild=? and member=? and name=?",
                            (round(product / 2, 2), guild, member, "drugs")):
                        pass
                    channel_id = await get_channel(guild, "info")
                    member = self.bot.get_guild(guild).get_member(member)
                    if member is None:
                        continue
                    channel = self.bot.get_guild(guild).get_channel(channel_id)
                    if channel is not None:
                        await channel.send(
                            f"{member.mention}, your drug distribution business was busted by the police. They took half of your product. Upgrade your business to prevent this in the future.")
                    else:
                        with contextlib.suppress(disnake.HTTPException, disnake.Forbidden):
                            await member.send(
                                f"{member.mention}, your drug distribution business on {self.bot.get_guild(guild).name} was busted by the police. They took half of your product. Upgrade your business to prevent this in the future.")
            await self.bot.db.commit()

    @cops_loop.before_loop
    async def before_cops_loop(self):
        await self.bot.wait_until_ready()

    @supplies_loop.before_loop
    async def before_supplies_loop(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Drugs(bot))
