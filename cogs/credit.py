import time

import aiosqlite
import disnake
from disnake.ext import commands, tasks
from db import get_balance, set_balance, credit_add, get_channel
from main import get_discord_date


class CreditView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(disnake.ui.Button(label="Pay Now", style=disnake.ButtonStyle.blurple))


class Credit(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot
        self.check_bills.start()

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("""CREATE TABLE IF NOT EXISTS credit(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild INTEGER,
                member INTEGER,
                channel INTEGER,
                message INTEGER,
                amount FLOAT,
                due_date INTEGER
            )"""):
                pass
            await db.commit()
            async with db.execute(
                    "SELECT id,amount,guild,message,due_date FROM credit WHERE guild=? and message=? and member=?",
                    (inter.guild_id, inter.message.id, inter.author.id)) as cursor:
                try:
                    id, amount, guild, message_id, due_date = await cursor.fetchone()
                except Exception:
                    return
                if due_date - (24 * 3600) > time.time():
                    embed = disnake.Embed(title="Credit Bill", color=disnake.Color.blurple())
                    embed.add_field(inline=False, name="Amount Owed", value=f"${amount}")
                    embed.add_field(inline=False, name="Due Date", value=get_discord_date(due_date))
                    embed.add_field(inline=False, name="Message",
                                    value=f"You have to wait until {get_discord_date(due_date) - (3600 * 24)} to pay your bill.")
                    await inter.response.edit_message(embed=embed)
                else:
                    try:
                        message = await inter.channel.fetch_message(message_id)
                        await message.delete()
                    except:
                        pass
                    await inter.channel.send(
                        f"{inter.author.mention}, you have successfully paid your bill. You have been charged {round(amount * 1.5, 2)}")
                    bal = await get_balance(inter.guild_id, inter.author.id)
                    await set_balance(inter.guild_id, inter.author.id, bal - (amount * 1.5))
                    async with db.execute("DELETE FROM credit WHERE message=?", (message_id,)):
                        pass
                    await db.commit()

    @commands.slash_command(name="credit")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.guild_only()
    async def credit_apply(self, inter: disnake.ApplicationCommandInteraction,
                           amount: int = commands.Param(description="The amount of credit you want")):
        channel = await get_channel(inter.guild_id, "bills")
        if channel is None:
            await inter.response.send_message(
                "A bills channel has not been set for this server. Set one by doing /setchannel bills #channel",
                ephemeral=True)
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        if amount < 1:
            await inter.response.send_message("The amount must be at least 1.", ephemeral=True)
            return
        bal = bal + 1 if bal <= 0 else bal
        if amount > bal * 5:
            await inter.response.send_message(f"You can only request 5x your current balance ({round(bal * 5, 2)}).",
                                              ephemeral=True)
            return
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("""CREATE TABLE IF NOT EXISTS credit(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild INTEGER,
                member INTEGER,
                channel INTEGER,
                message INTEGER,
                amount FLOAT,
                due_date INTEGER
            )"""):
                pass
            await db.commit()
            async with db.execute("SELECT * FROM credit WHERE guild=? and member=?",
                                  (inter.guild_id, inter.author.id)) as cursor:
                if await cursor.fetchone() is not None:
                    await inter.response.send_message("You already have an unpaid credit bill.", ephemeral=True)
                    return
        embed = disnake.Embed(title="Credit Bill", color=disnake.Color.blurple())
        embed.add_field(inline=False, name="Amount Owed", value=f"${amount}")
        embed.add_field(inline=False, name="Due Date", value=get_discord_date(time.time() + 3600 * 48))
        msg = await inter.guild.get_channel(channel).send(embed=embed, view=CreditView())
        await credit_add(inter.guild_id, inter.author.id, amount, msg.id, inter.channel_id)
        await inter.response.send_message(
            f"You have been paid ${round(amount, 2)}. You must pay your bill within 48 hours or you will be charged ${round(amount * 2, 2)}")

    @tasks.loop(seconds=10)
    async def check_bills(self):
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("""CREATE TABLE IF NOT EXISTS credit(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild INTEGER,
                member INTEGER,
                channel INTEGER,
                message INTEGER,
                amount FLOAT,
                due_date INTEGER
            )"""):
                pass
            await db.commit()
            async with db.execute("SELECT id,guild,member,amount,due_date,message,channel FROM credit") as cursor:
                async for entry in cursor:
                    id, guild, member, amount, due_date, message, channel = entry
                    async with await db.execute("DELETE FROM credit WHERE id=?", (id,)):
                        pass
                    if time.time() >= due_date:
                        guild = self.bot.get_guild(guild)
                        if guild is None:
                            continue
                        channel = guild.get_channel(channel)
                        if channel is None:
                            continue
                        try:
                            await channel.fetch_message(message)
                        except Exception:
                            continue
                        member = guild.get_member(member)
                        if member is not None:
                            await channel.send(
                                f"{member.mention}, You have failed to pay your bill on time. You have been charged ${round(amount * 2, 2)}")
                            await set_balance(guild.id, member.id, (await get_balance(guild.id, member.id)) - 1)

    @check_bills.before_loop
    async def before_bills_check(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Credit(bot))