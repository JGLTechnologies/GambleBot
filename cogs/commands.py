import random
import disnake
from disnake.ext import commands
from db import set_balance, get_balance, set_channel, get_channel, has_security
from main import get_discord_date
from limits.aio.strategies import MovingWindowRateLimiter
from limits.aio.storage import MemoryStorage
from limits import RateLimitItemPerHour, RateLimitItemPerMinute
from main import int_to_money


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot
        self.storage: MemoryStorage = MemoryStorage()
        self.moving_window: MovingWindowRateLimiter = MovingWindowRateLimiter(self.storage)
        self.hour: RateLimitItemPerHour = RateLimitItemPerHour(1, 1)
        self.minute_items = {}

    def get_minute_item(self, minutes: int) -> RateLimitItemPerMinute:
        item = self.minute_items.get(minutes)
        if item is not None:
            return item
        item = RateLimitItemPerMinute(1, minutes)
        self.minute_items[minutes] = item
        return item

    @commands.guild_only()
    @commands.slash_command(name="cleardebt")
    async def clear_debt(self, inter: disnake.ApplicationCommandInteraction):
        if not await self.moving_window.test(self.get_minute_item(20160),
                                             "clear_debt", inter.guild_id, inter.author.id):
            reset_time, _ = await self.moving_window.get_window_stats(self.get_minute_item(15),
                                                                      "clear_debt", inter.guild_id,
                                                                      inter.author.id)
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        if await get_balance(inter.guild_id, inter.author.id) >= 0:
            await inter.response.send_message("You are not in any debt.", ephemeral=True)
        else:
            await self.moving_window.hit(self.get_minute_item(20160), "clear_debt", inter.guild_id, inter.author.id)
            await set_balance(inter.guild_id, inter.author.id, 0)
            await inter.response.send_message("Your debt has been cleared.")

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.slash_command(name="errors", guild_ids=[844418702430175272])
    async def errors(self, inter: disnake.ApplicationCommandInteraction):
        with open("GambleBot.log", "rb") as f:
            file = disnake.File(f, "GambleBot.txt")
            await inter.response.send_message(file=file, ephemeral=True)

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.slash_command(name="setbalance")
    async def set_balance_command(self, inter: disnake.ApplicationCommandInteraction,
                                  member: disnake.Member = commands.Param(),
                                  balance: int = commands.Param()):
        await set_balance(inter.guild_id, member.id, balance)
        await inter.response.send_message(f"Set {str(member)}'s balance to {int_to_money(balance)}.", ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(name="balance")
    async def balance_command(self, inter: disnake.ApplicationCommandInteraction,
                              member: disnake.Member = commands.Param(default=None)):
        bal = await get_balance(inter.guild_id, member.id if member is not None else inter.author.id)
        await inter.response.send_message(f"{str(member or inter.author)}'s balance is {int_to_money(bal)}.")

    @commands.slash_command(name="ping")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(f"Ping: {round(self.bot.latency, 2)}ms")

    @commands.guild_only()
    @commands.slash_command(name="accinfo")
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
        embed.set_thumbnail(url=member.avatar.url if member.avatar is not None else member.default_avatar.url)
        await inter.response.send_message(embed=embed)

    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.slash_command(name="setchannel")
    async def set_channel(self, inter: disnake.ApplicationCommandInteraction,
                          name: str = commands.Param(description="The channel you want to set"),
                          channel: disnake.TextChannel = commands.Param()):
        if name.lower() not in {"bills", "info"}:
            await inter.response.send_message(
                "Invalid channel name. Do `/config` to se valid channel names.",
                ephemeral=True)
            return
        await set_channel(guild_id=inter.guild_id, channel_name=name.lower(), channel_id=channel.id)
        await inter.response.send_message(f"Successfully set the {name} channel to {channel.mention}", ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(name="config")
    async def get_config(self, inter: disnake.ApplicationCommandInteraction):
        bills = await get_channel(inter.guild_id, "bills")
        info = await get_channel(inter.guild_id, "info")
        bills = self.bot.get_channel(bills)
        info = self.bot.get_channel(info)
        embed = disnake.Embed(title=f"Config For {inter.guild.name}", color=disnake.Color.blurple())
        embed.add_field(inline=False, name="Channels",
                        value=f"Bills: {bills.mention if bills is not None else 'Not Set'}\nInfo: {info.mention if info is not None else 'Not Set'}")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(name="rob")
    async def rob(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = commands.Param()):
        if not await self.moving_window.test(self.get_minute_item(15),
                                             "rob_use", inter.guild_id, inter.author.id):
            reset_time, _ = await self.moving_window.get_window_stats(self.get_minute_item(15),
                                                                      "rob_use", inter.guild_id,
                                                                      inter.author.id)
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        if not await self.moving_window.test(self.hour, "rob", inter.guild_id, str(member.id)):
            await inter.response.send_message("That member was already robbed recently.", ephemeral=True)
            return
        bal = await get_balance(inter.guild_id, member.id)
        if bal < 1000:
            await inter.response.send_message("That member is too poor to be robbed.", ephemeral=True)
            return
        await self.moving_window.hit(self.get_minute_item(15), "rob_use", inter.guild_id, inter.author.id)
        if await has_security(inter.guild_id, member.id):
            chances = ["s", "f", "f", "f", "f", "f", "f", "f", "f", "f"]
        else:
            chances = ["s", "s", "s", "s", "s", "f", "f", "f", "f", "f"]
        success = random.choice(chances) == "s"
        if success:
            await self.moving_window.hit(self.hour, inter.guild_id, str(member.id))
            percent = random.randrange(1, 50)
            amount = bal * (percent / 100)
            msg = f"You stole ${amount} from {str(member)}."
            await set_balance(inter.guild_id, inter.author.id,
                              (await get_balance(inter.guild_id, inter.author.id) + amount))
            await set_balance(inter.guild_id, member.id,
                              (await get_balance(inter.guild_id, member.id) - amount))
        else:
            msg = f"You failed to rob {str(member)}. You have been fined $1000 dollars."
            await set_balance(inter.guild_id, inter.author.id,
                              (await get_balance(inter.guild_id, inter.author.id) - 1000))
        await inter.response.send_message(msg)

    @commands.guild_only()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.slash_command(name="work")
    async def work_command(self, inter: disnake.ApplicationCommandInteraction):
        bal = await get_balance(inter.guild_id, inter.author.id)
        if random.randrange(0, 25) == 1:
            desc = "You hurt yourself while working, so you sued the company for $5000. You now have {money}."
            pay = 5000
        else:
            job_list = [{"desc": "You drove someone in a taxi! They gave you {pay}! You now have {money}.",
                         "pay": [100, 150, 125, 175]},
                        {"desc": "You worked as a cashier for 8 hours and made {pay}! You now have {money}.",
                         "pay": [50, 60, 70, 80, 90, 100, 125]},
                        {"desc": "You uploaded a video and made {pay}! You now have {money}.",
                         "pay": [100, 200, 300, 400, 500]}]
            job = random.choice(job_list)
            pay = random.choice(job["pay"])
            desc = job["desc"]
        msg = desc.format(pay=pay, money=round(bal + pay, 2))
        await inter.response.send_message(msg)
        await set_balance(inter.guild_id, inter.author.id, bal + pay)

    @commands.slash_command(name="commands")
    async def help_command(self, inter: disnake.ApplicationCommandInteraction):
        role_shop = [{"name": "Role Add", "usage": "`/role add role:[role] price:[integer]`",
                      "desc": "Add a role to the role shop"},
                     {"name": "Role Remove", "usage": "`/role add role:[role]`",
                      "desc": "Remove a role from the role shop"},
                     {"name": "Role Shop", "usage": "`/role shop`",
                      "desc": "Display the role shop"},
                     {"name": "Role Buy", "usage": "`/role buy role:[role]`",
                      "desc": "Buy a role from the role shop"}]
        business = [{"name": "Steal Drugs", "usage": "`/drugs steal`",
                     "desc": "Steal supplies to make drugs"},
                    {"name": "Sell Drugs", "usage": "`/drugs sell`",
                     "desc": "Sells all of the drugs in your inventory"},
                    {"name": "Upgrade Drug Distribution Business", "usage": "`/drugs upgrade`",
                     "desc": "Raises your business's production speed and lowers chances of being caught by the cops. Costs $200,000.",
                     "admin": False}, {"name": "Drug Info", "usage": "`/drugs info`",
                                       "desc": "Displays info for your drug distribution business.",
                                       "admin": False}
                    ]
        admin = [{"name": "Account Info", "usage": "`/accinfo member:[optional member]`",
                  "desc": "Shows information for an account"},
                 {"name": "Set Channel", "usage": "`/setchannel name:[channel]`",
                  "desc": "Chooses the channel for a certain purpose"},
                 {"name": "Clear Credit Bills", "usage": "`/clearcreditbills member:[optional member]`",
                  "desc": "Clears the credit card bill from a member"},
                 {"name": "Server Configuration", "usage": "`/config`",
                  "desc": "Shows the bot configuration for the server"}]
        shop = [{"name": "Unsubscribe", "usage": "`/unsubscribe service:[text]`",
                 "desc": "Unsubscribe from a payment plan"},
                {"name": "Shop", "usage": "`/shop`",
                 "desc": "View all of the items available for purchase on the server"},
                {"name": "Buy Item", "usage": "`/buyitem item:[text]`",
                 "desc": "Allows you to buy an item from the shop"}]
        economy = [{"name": "Apply For Credit", "usage": "`/credit amount:[integer]`",
                    "desc": "Get money using the credit system, you will have to pay back the amount you owe later.",
                    "admin": False}, {"name": "Work", "usage": "`/work`", "desc": "Work for money"},
                   {"name": "Rob", "usage": "`/rob member:[member]`",
                    "desc": "Rob someone to get a percent of their money"},
                   {"name": "Balance", "usage": "`/balance member:[optional member]`",
                    "desc": "Shows the balance of either you or another person"},
                   {"name": "Beg", "usage": "`/beg`",
                    "desc": "Beg for money!"},
                   {"name": "Invest", "usage": "`/invest amount:[integer]`",
                    "desc": "Invest in the stock market to go big or make nothing"},
                   {"name": "Pay", "usage": "`/pay member:[member] amount:[integer]`",
                    "desc": "Pay another member"}]
        misc = [{"name": "Invite", "usage": "`/invite`",
                 "desc": "Get a link to invite GambleBot to your server"},
                {"name": "Ping", "usage": "`/ping`", "desc": "Shows the latency of the bot"}]
        games = [{"name": "Rock Paper Scissors Start", "usage": "`/rps start`",
                  "desc": "Starts a game of Rock Paper Scissors for money"},
                 {"name": "Rock Paper Scissors Cancel", "usage": "`/rps cancel`",
                  "desc": "Cancels your current Rock Paper Scissors game"},
                 {"name": "Blackjack Start", "usage": "`/blackjack start`",
                  "desc": "Starts a game of Blackjack for money"},
                 {"name": "Blackjack Cancel", "usage": "`/blackjack cancel`",
                  "desc": "Cancels your current Blackjack game"}]
        economy_str = ""
        business_str = ""
        admin_str = ""
        misc_str = ""
        games_str = ""
        shop_str = ""
        role_str = ""
        for command in economy:
            economy_str += f"Command Name: {command['name']}\nUsage: {command['usage']}\nDescription: {command['desc']}\n\n"
        for command in business:
            business_str += f"Command Name: {command['name']}\nUsage: {command['usage']}\nDescription: {command['desc']}\n\n"
        for command in games:
            games_str += f"Command Name: {command['name']}\nUsage: {command['usage']}\nDescription: {command['desc']}\n\n"
        for command in misc:
            misc_str += f"Command Name: {command['name']}\nUsage: {command['usage']}\nDescription: {command['desc']}\n\n"
        for command in shop:
            shop_str += f"Command Name: {command['name']}\nUsage: {command['usage']}\nDescription: {command['desc']}\n\n"
        for command in role_shop:
            role_str += f"Command Name: {command['name']}\nUsage: {command['usage']}\nDescription: {command['desc']}\n\n"
        for command in admin:
            admin_str += f"Command Name: {command['name']}\nUsage: {command['usage']}\nDescription: {command['desc']}\n\n"
        embed = disnake.Embed(title="Commands", color=disnake.Color.blurple())
        embed.add_field(name="**Admin**", value=admin_str, inline=False)
        embed.add_field(name="**Economy**", value=economy_str, inline=False)
        embed.add_field(name="**Businesses**", value=business_str, inline=False)
        embed.add_field(name="**Role Shop**", value=role_str, inline=False)
        embed.add_field(name="**Games**", value=games_str, inline=False)
        embed.add_field(name="**Shop**", value=shop_str, inline=False)
        embed.add_field(name="**Misc**", value=misc_str, inline=False)
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(name="beg")
    async def beg_command(self, inter: disnake.ApplicationCommandInteraction):
        if not await self.moving_window.test(self.get_minute_item(1),
                                             "beg", inter.guild_id, inter.author.id):
            reset_time, _ = await self.moving_window.get_window_stats(self.get_minute_item(1),
                                                                      "beg", inter.guild_id,
                                                                      inter.author.id)
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        if bal >= 1000:
            await inter.response.send_message("You are too rich to beg.", ephemeral=True)
            return
        await self.moving_window.hit(self.get_minute_item(10), "beg", inter.guild_id, inter.author.id)
        if random.randrange(0, 25) == 1:
            desc = "Congrats! Some generous rich man gave you $1000. You now have {money}."
            pay = 1000
        else:
            beg_list = [{"desc": "Some woman walking by pitied you, so she gave you {pay}. You now have {money}.",
                         "pay": [10, 12, 13, 15, 17, 20]},
                        {"desc": "An old man walked by and gave you {pay}. You now have {money}.",
                         "pay": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 40]},
                        {"desc": "It's your lucky day! You found {pay} on the road!. You now have {money}.",
                         "pay": [1, 1, 1, 1, 1, 5, 5, 5, 10, 10, 10, 20, 50, 100]},
                        {"desc": "You made nothing during your begging session today.", "pay": [0]},
                        {
                            "desc": "You tried to steal a purse from an old lady! You were fined {pay}. You now have {money}.",
                            "pay": [-1, -3, -5, -7, -9, -10, -15]},
                        {
                            "desc": "You stole a purse from an old lady! You got {pay}. You now have {money}.",
                            "pay": [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 30, 30, 30, 30, 30, 50, 70, 90, 100, 150]}]
            beg = random.choice(beg_list)
            pay = random.choice(beg["pay"])
            desc = beg["desc"]
        msg = desc.format(pay=abs(pay), money=round(bal + pay, 2))
        await inter.response.send_message(msg)
        await set_balance(inter.guild_id, inter.author.id, bal + pay)

    @commands.guild_only()
    @commands.slash_command(name="invest")
    async def invest_command(self, inter: disnake.ApplicationCommandInteraction, amount: int = commands.Param()):
        if not await self.moving_window.test(self.get_minute_item(1),
                                             "invest", inter.guild_id, inter.author.id):
            reset_time, _ = await self.moving_window.get_window_stats(self.get_minute_item(1),
                                                                      "invest", inter.guild_id,
                                                                      inter.author.id)
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        if bal < amount:
            await inter.response.send_message("You do not have enough money.", ephemeral=True)
            return
        await self.moving_window.hit(self.get_minute_item(1), "invest", inter.guild_id, inter.author.id)
        if random.randrange(0, 25) == 1:
            desc = "The market spiked and you made {pay}. You now have {money}."
            percent = 500
        else:
            stock_list = [{
                "desc": "There was a slight increase in the market, and you made {pay} in return! You now have {money}.",
                "percent": [110, 111, 112, 113, 114, 115, 117, 120]},
                {"desc": "The Stock Market crashed, and you lost {pay}! You now have {money}.",
                 "percent": [10, 20, 30, 40, 50]},
                {
                    "desc": "There was a slight decrease in the market, and you lost {pay}! You now have {money}.",
                    "percent": [90, 85, 75, 92, 93, 87, 65, 70, 76]}, {
                    "desc": "There was a slight decrease in the market, and you lost {pay}! You now have {money}.",
                    "percent": [91, 83, 75, 92, 93, 70, 90, 80, 75]},
                {"desc": "There was a spike in the market, and you made {pay}! You now have {money}.",
                 "percent": [150, 165, 175, 180, 190, 200, 220, 160, 170, 155, 300]}, {
                    "desc": "There was a slight increase in the market, and you made {pay} in return! You now have {money}.",
                    "percent": [115, 141, 122, 143, 114, 135, 119, 120]}]
            stock = random.choice(stock_list)
            percent = random.choice(stock["percent"])
            desc = stock["desc"]
        msg = desc.format(pay=int_to_money(abs((percent / 100) * amount - amount)),
                          money=int_to_money(bal + ((percent / 100) * amount - amount)))
        await inter.response.send_message(msg)
        await set_balance(inter.guild_id, inter.author.id, bal + ((percent / 100) * amount - amount))

    @commands.guild_only()
    @commands.slash_command(name="pay")
    async def pay_command(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = commands.Param(),
                          amount: int = commands.Param()):
        if not await self.moving_window.test(self.get_minute_item(1),
                                             "pay", inter.guild_id, inter.author.id):
            reset_time, _ = await self.moving_window.get_window_stats(self.get_minute_item(5),
                                                                      "pay", inter.guild_id,
                                                                      inter.author.id)
            await inter.response.send_message(
                f"You need to wait until {get_discord_date(reset_time)} to use that command again.", ephemeral=True)
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        if amount > bal:
            await inter.response.send_message("You do not have enough money.", ephemeral=True)
            return
        await self.moving_window.hit(self.get_minute_item(1), "pay", inter.guild_id, inter.author.id)
        await inter.response.send_message(f"Successfully paid {str(member)} ${amount}.")
        await set_balance(inter.guild_id, inter.author.id, bal - amount)
        await set_balance(inter.guild_id, member.id, await get_balance(inter.guild_id, member.id) + amount)

    @commands.slash_command(name="invite")
    async def invite_command(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(
            f"Invite Link: [click](https://discord.com/api/oauth2/authorize?client_id=929595364821074020&permissions=8&scope=bot%20applications.commands)")


def setup(bot):
    bot.add_cog(Commands(bot))
