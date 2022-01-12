import random
import disnake
from disnake.ext import commands
from db import set_balance, get_balance, set_channel, get_channel, has_security
from main import get_discord_date


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot

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

    @commands.slash_command(name="accinfo")
    @commands.guild_only()
    async def account_info(self, inter: disnake.ApplicationCommandInteraction,
                           member: disnake.Member = commands.Param(default=None)):
        if member is None:
            member = inter.author

        embed = disnake.Embed(title=f"Info For {str(member)}", color=disnake.Color.blurple())
        embed.add_field(name="Account Creation Date", value=get_discord_date(member.created_at.timestamp()))
        embed.add_field(name="Server Join Date", value=get_discord_date(member.joined_at.timestamp()))
        embed.add_field(name="Roles",
                        value=", ".join([role.mention for role in member.roles if role.name != "@everyone"]))
        embed.add_field(name="Display Name", value=member.display_name)
        embed.add_field(name="ID", value=member.id)
        embed.set_thumbnail(url=member.avatar.url or member.default_avatar.url)
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="setchannel")
    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    async def set_channel(self, inter: disnake.ApplicationCommandInteraction,
                          name: str = commands.Param(description="The channel you want to set"),
                          channel: disnake.TextChannel = commands.Param()):
        if name.lower() not in {"bills"}:
            await inter.response.send_message(
                "Invalid channel name. Visit https://jgltechnologies.com/GambleBot/config#channels to view all of the "
                "valid channel names.",
                ephemeral=True)
            return
        await set_channel(guild_id=inter.guild_id, channel_name=name.lower(), channel_id=channel.id)
        await inter.response.send_message(f"Successfully set the {name} channel to {channel.mention}", ephemeral=True)

    @commands.slash_command(name="config")
    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    async def get_config(self, inter: disnake.ApplicationCommandInteraction):
        bills = await get_channel(inter.guild_id, "bills")
        bills = self.bot.get_channel(bills)
        embed = disnake.Embed(title=f"Config For {inter.guild.name}", color=disnake.Color.blurple())
        embed.add_field(inline=False, name="Channels",
                        value=f"Bills: {bills.mention if bills is not None else 'Not Set'}")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="rob")
    @commands.guild_only()
    @commands.cooldown(1, 1200, commands.BucketType.member)
    async def rob(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = commands.Param()):
        bal = await get_balance(inter.guild_id, member.id)
        if bal < 1000:
            await inter.response.send_message("That member is too poor to be robbed.", ephemeral=True)
            return
        if await has_security(inter.guild_id, member.id):
            chances = ["s", "f", "f", "f", "f", "f", "f", "f", "f", "f"]
        else:
            chances = ["s", "s", "s", "s", "f", "f", "f", "f", "f", "f"]
        success = random.choice(chances) == "s"
        if success:
            percent = random.randrange(1, 50)
            amount = bal * (percent / 100)
            msg = f"You stole ${round(amount, 2)} from {str(member)}."
            await set_balance(inter.guild_id, inter.author.id,
                              (await get_balance(inter.guild_id, inter.author.id) + amount))
            await set_balance(inter.guild_id, member.id,
                              (await get_balance(inter.guild_id, member.id) - amount))
        else:
            msg = f"You failed to rob {str(member)}. You have been fined $1000 dollars."
            await set_balance(inter.guild_id, inter.author.id,
                              (await get_balance(inter.guild_id, inter.author.id) - 1000))
        await inter.response.send_message(msg)

    @commands.slash_command(name="work")
    @commands.guild_only()
    @commands.cooldown(1, 900, commands.BucketType.member)
    async def work_command(self, inter: disnake.ApplicationCommandInteraction):
        bal = await get_balance(inter.guild_id, inter.author.id)
        if random.randrange(0, 25) == 1:
            desc = "You hurt yourself while working, so you sued the company for $5000. You now have ${money}."
            pay = 5000
        else:
            job_list = [{"desc": "You drove someone in a taxi! They gave you ${pay}! You now have ${money}.",
                         "pay": [100, 150, 125, 175]},
                        {"desc": "You worked as a cashier for 8 hours and made ${pay}! You now have ${money}.",
                         "pay": [50, 60, 70, 80, 90, 100, 125]},
                        {"desc": "You uploaded a video and made ${pay}! You now have ${money}.",
                         "pay": [100, 200, 300, 400, 500]}]
            job = random.choice(job_list)
            pay = random.choice(job["pay"])
            desc = job["desc"]
        msg = desc.format(pay=pay, money=round(bal + pay, 2))
        await inter.response.send_message(msg)
        await set_balance(inter.guild_id, inter.author.id, bal + pay)

    @commands.slash_command(name="commands")
    async def help_command(self, inter: disnake.ApplicationCommandInteraction):
        commands = [{"name": "Rock Paper Scissors", "usage": "`/rps bet:[integer]`",
                     "desc": "Stats a game of rock paper scissors for money.", "admin": False},
                    {"name": "Account Info", "usage": "`/accinfo member:[optional member]`",
                     "desc": "Shows information for an account.", "admin": False},
                    {"name": "Apply For Credit", "usage": "`/credit amount:[integer]`",
                     "desc": "Get money using the credit system, you will have to pay back the amount you owe later.",
                     "admin": False},
                    {"name": "Set Channel", "usage": "`/setchannel name:[channel]`",
                     "desc": "Chooses the channel for the credit and security bills.", "admin": True},
                    {"name": "Work", "usage": "`/work`", "desc": "Work for money", "admin": False},
                    {"name": "Rob", "usage": "`/rob member:[member]`",
                     "desc": "Rob someone to get a percent of their money.", "admin": False},
                    {"name": "Balance", "usage": "`/balance member:[optional member]`",
                     "desc": "Shows the balance of either you or another person.", "admin": False},
                    {"name": "Clear Credit Bills", "usage": "`/clearcreditbills member:[optional member]`",
                     "desc": "Clears the credit card bill from a member.", "admin": True},
                    {"name": "Ping", "usage": "`/ping`", "desc": "Shows the latency of the bot.", "admin": True},
                    {"name": "Server Configuration", "usage": "`/config`",
                     "desc": "Shows the bot configuration for the server.", "admin": True},
                    {"name": "Buy Item", "usage": "`/buyitem item:[text]`",
                     "desc": "Allows you to buy an item from the shop.", "admin": False},
                    {"name": "Beg", "usage": "`/beg`",
                     "desc": "Beg for money!", "admin": False},
                    {"name": "Invest", "usage": "`/invest amount:[integer]`",
                     "desc": "Invest in the stock market to go big or make nothing.", "admin": False}]
        if not (inter.author.guild_permissions.administrator and inter.author.top_role.permissions.administrator):
            commands = [command for command in commands if not command["admin"]]
        msg = ""
        for command in commands:
            msg += f"**Command Name:** {command['name']}\n**Usage:** {command['usage']}\n**Description:** {command['desc']}\n\n"
            embed = disnake.Embed(title="Commands", color=disnake.Color.blurple(), description=msg)
        await inter.response.send_message(embed=embed, ephemeral=True)



def setup(bot):
    bot.add_cog(Commands(bot))
