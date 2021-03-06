import contextlib
import time
import disnake
from disnake.ext import commands, tasks
from db import get_balance, set_balance, credit_add, get_channel
from main import get_discord_date
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter
from limits import RateLimitItemPerDay


class CreditView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(disnake.ui.Button(label="Pay Now", style=disnake.ButtonStyle.blurple))


class Credit(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot
        self.check_bills.start()
        self.storage: MemoryStorage = MemoryStorage()
        self.moving_window: MovingWindowRateLimiter = MovingWindowRateLimiter(self.storage)
        self.item: RateLimitItemPerDay = RateLimitItemPerDay(1, 1)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        async with self.bot.db.execute("""CREATE TABLE IF NOT EXISTS credit(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild INTEGER,
                member INTEGER,
                message INTEGER,
                amount FLOAT,
                due_date INTEGER
            )"""):
            pass
        await self.bot.db.commit()
        async with self.bot.db.execute(
                "SELECT id,amount,guild,message,due_date,member FROM credit WHERE guild=? and message=? and member=?",
                (inter.guild_id, inter.message.id, inter.author.id)) as cursor:
            try:
                id, amount, guild, message_id, due_date, member_id = await cursor.fetchone()
            except Exception:
                return
            if inter.author.id != member_id:
                return
            bal = await get_balance(inter.guild_id, inter.author.id)
            if bal - amount * 1.5 < 0:
                await inter.response.send_message("You do not have enough money.", ephemeral=True)
                return
            with contextlib.suppress(disnake.Forbidden, disnake.HTTPException):
                message = await inter.channel.fetch_message(message_id)
                await message.delete()
            await inter.channel.send(
                f"{inter.author.mention}, you have successfully paid your bill. You have been charged ${amount * 1.5}")
            await set_balance(inter.guild_id, inter.author.id, bal - (amount * 1.5))
            async with self.bot.db.execute("DELETE FROM credit WHERE id=?", (id,)):
                pass
            await self.bot.db.commit()

    @commands.guild_only()
    @commands.slash_command(name="credit")
    async def credit_apply(self, inter: disnake.ApplicationCommandInteraction,
                           amount: int = commands.Param(description="The amount of credit you want")):
        if not await self.moving_window.test(self.item, inter.author.id, inter.guild_id):
            reset_time, _ = await self.moving_window.get_window_stats(self.item,
                                                                      inter.author.id, inter.guild_id)
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        channel = await get_channel(inter.guild_id, "bills")
        if channel is None:
            await inter.response.send_message(
                "A bills channel has not been set for this server. Set one by doing /setchannel Bills #channel",
                ephemeral=True)
            return
        balance = await get_balance(inter.guild_id, inter.author.id)
        if amount < 1:
            await inter.response.send_message("The amount must be at least 1.", ephemeral=True)
            return
        bal = 100 if balance < 100 else balance
        if amount > bal * 5:
            await inter.response.send_message(f"You can only request 5x your current balance (${bal * 5}).",
                                              ephemeral=True)
            return
            async with self.bot.db.execute("""CREATE TABLE IF NOT EXISTS credit(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild INTEGER,
                member INTEGER,
                message INTEGER,
                amount FLOAT,
                due_date INTEGER
            )"""):
                pass
            await self.bot.db.commit()
            async with self.bot.db.execute("SELECT id,message FROM credit WHERE guild=? and member=?",
                                           (inter.guild_id, inter.author.id)) as cursor:
                entry = await cursor.fetchone()
                if entry is not None:
                    id, msg = entry
                    try:
                        await inter.guild.get_channel(channel).fetch_message(msg)
                        await inter.response.send_message("You already have an unpaid credit bill.", ephemeral=True)
                        return
                    except disnake.NotFound:
                        async with self.bot.db.execute("DELETE FROM credit WHERE id=?", (id,)):
                            pass
                        await self.bot.db.commit()
        await self.moving_window.hit(self.item, [str(inter.author.id), str(inter.guild_id)])
        embed = disnake.Embed(title="Credit Bill", color=disnake.Color.blurple())
        embed.add_field(inline=False, name="Amount Owed", value=f"${amount * 1.5}")
        embed.add_field(inline=False, name="Due Date", value=get_discord_date(time.time() + 3600 * 48))
        msg = await inter.guild.get_channel(channel).send(inter.author.mention, embed=embed, view=CreditView())
        await credit_add(inter.guild_id, inter.author.id, amount, msg.id, inter.channel_id)
        await set_balance(inter.guild_id, inter.author.id, balance + amount)
        await inter.response.send_message(
            f"You have been paid ${amount}. You must pay your bill within 48 hours or you will be charged ${amount * 2}",
            ephemeral=True)

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.slash_command(name="clearcreditbills")
    async def clear_bills(self, inter: disnake.ApplicationCommandInteraction,
                          member: disnake.Member = commands.Param(default=None)):
        member = member or inter.author
        await inter.response.send_message(f"{str(member)}'s credit bills have been cleared.", ephemeral=True)
        async with self.bot.db.execute("DELETE FROM credit WHERE member=?", (member.id,)):
            pass
        await self.bot.db.commit()

    @tasks.loop(seconds=10)
    async def check_bills(self):
        async with self.bot.db.execute("""CREATE TABLE IF NOT EXISTS credit(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild INTEGER,
                    member INTEGER,
                    message INTEGER,
                    amount FLOAT,
                    due_date INTEGER
                )"""):
            pass
        await self.bot.db.commit()
        async with self.bot.db.execute("SELECT id,guild,member,amount,due_date,message FROM credit") as cursor:
            async for entry in cursor:
                id, guild, member, amount, due_date, message = entry
                if time.time() >= due_date:
                    channel = await get_channel(guild, "bills")
                    async with self.bot.db.execute("DELETE FROM credit WHERE id=?", (id,)):
                        pass
                    await self.bot.db.commit()
                    guild = self.bot.get_guild(guild)
                    if guild is None:
                        continue
                    channel = guild.get_channel(channel)
                    if channel is None:
                        continue
                    try:
                        await channel.fetch_message(message)
                    except disnake.NotFound:
                        continue
                    member = guild.get_member(member)
                    if channel is not None:
                        await channel.send(
                            f"{member.mention}, you have failed to pay your credit bill on time. You have been charged ${amount * 2}")
                        await set_balance(guild.id, member.id, (await get_balance(guild.id, member.id)) - 1)
                    else:
                        with contextlib.suppress(disnake.HTTPException, disnake.Forbidden):
                            await member.send(
                                f"{member.mention}, you have failed to pay your credit bill on {guild.name} on time. You have been charged ${amount * 2}")

    @check_bills.before_loop
    async def before_bills_check(self):
        await self.bot.wait_until_ready()

    @check_bills.error
    async def error(self, *args):
        pass


def setup(bot):
    bot.add_cog(Credit(bot))
