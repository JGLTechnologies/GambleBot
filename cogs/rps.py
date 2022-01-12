import random
from db import set_balance, get_balance
import disnake
from disnake.ext import commands
from collections import defaultdict

rps_games = defaultdict(lambda: {})


class RPS(disnake.ui.Select):
    def __init__(self, bet: int):
        self.bet = bet
        options = [
            disnake.SelectOption(
                label="Rock"
            ),
            disnake.SelectOption(
                label="Paper"
            ),
            disnake.SelectOption(
                label="Scissors"
            ),
        ]

        super().__init__(
            placeholder="Choose rock, paper, or scissors",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        if self.view.rps.bet > bal:
            self.bet = bal
        if bal <= 0:
            await inter.channel.send("You are out of money.", delete_after=7)
            try:
                msg = await inter.channel.fetch_message(rps_games[inter.guild_id][self.view.author][0])
                await msg.delete()
            except Exception:
                pass
            return
        player_choice = self.values[0].lower()
        computer_choice = random.choice(["rock", "paper", "scissors"])
        if player_choice == computer_choice:
            embed = disnake.Embed(
                description=f"It's a tie!\nYour current balance: ${round(bal, 2)}\nBet: ${self.bet}",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
        elif player_choice == "rock" and computer_choice == "scissors":
            bal += self.bet
            embed = disnake.Embed(
                description=f"You won!\nYour current balance: ${round(bal, 2)}\nBet: ${self.bet}",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
            await set_balance(inter.guild_id, inter.author.id, bal)
        elif player_choice == "paper" and computer_choice == "rock":
            bal += self.bet
            embed = disnake.Embed(
                description=f"You won!\nYour current balance: ${round(bal, 2)}\nBet: ${self.bet}",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
            await set_balance(inter.guild_id, inter.author.id, bal)
        elif player_choice == "scissors" and computer_choice == "paper":
            bal += self.bet
            embed = disnake.Embed(
                description=f"You won!\nYour current balance: ${round(bal, 2)}\nBet: ${self.bet}",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
            await set_balance(inter.guild_id, inter.author.id, bal)
        else:
            bal -= self.bet
            if self.view.rps.bet > bal:
                self.bet = bal
            if bal <= 0:
                await inter.channel.send(f"{inter.author.mention}, you are out of money.", delete_after=7)
                try:
                    msg = await inter.channel.fetch_message(rps_games[inter.guild_id][self.view.author][0])
                    await msg.delete()
                except Exception:
                    pass
                await set_balance(inter.guild_id, inter.author.id, bal)
                return
            embed = disnake.Embed(
                description=f"You lost!\nYour current balance: ${round(bal, 2)}\nBet: ${self.bet}",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
            await set_balance(inter.guild_id, inter.author.id, bal)
        await inter.response.edit_message(embed=embed)


class INCR(disnake.ui.Button):
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        if self.view.rps.bet + 1000 <= bal:
            self.view.rps.bet += 1000
        elif self.view.rps.bet + 100 <= bal:
            self.view.rps.bet += 100
        elif self.view.rps.bet + 10 <= bal:
            self.view.rps.bet += 10
        elif self.view.rps.bet + 1 <= bal:
            self.view.rps.bet += 1
        self.view.decr.style = disnake.ButtonStyle.red
        embed = disnake.Embed(
            description=f"Your current balance: ${round(bal, 2)}\nBet: ${self.view.rps.bet}",
            title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
        await inter.response.edit_message(embed=embed)


class DECR(disnake.ui.Button):
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        if self.view.rps.bet - 1000 > 0:
            self.view.rps.bet -= 1000
        elif self.view.rps.bet - 100 > 0:
            self.view.rps.bet -= 100
        elif self.view.rps.bet - 10 > 0:
            self.view.rps.bet -= 10
        elif self.view.rps.bet - 1 > 0:
            self.view.rps.bet -= 1
        self.view.incr.style = disnake.ButtonStyle.blurple
        embed = disnake.Embed(
            description=f"Your current balance: ${await get_balance(inter.guild_id, inter.author.id)}\nBet: ${self.view.rps.bet}",
            title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
        await inter.response.edit_message(embed=embed)


class RPSView(disnake.ui.View):
    def __init__(self, bet: int, author: int, guild: int, channel: int):
        super().__init__(timeout=3600)
        self.author = author
        self.channel = channel
        self.guild = guild
        self.rps = RPS(bet)
        self.incr = INCR(label="⏫", style=disnake.ButtonStyle.blurple)
        self.decr = DECR(label="⏬", style=disnake.ButtonStyle.red)
        self.add_item(self.incr)
        self.add_item(self.decr)
        self.add_item(self.rps)

    async def on_timeout(self) -> None:
        try:
            del rps_games[self.guild][self.author]
        except KeyError:
            return


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot

    @commands.slash_command(name="rps")
    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def rock_paper_scissors(self, inter: disnake.ApplicationCommandInteraction,
                                  bet: int = commands.Param(description="The amount you want to bet")):
        if inter.author.id in rps_games[inter.guild_id]:
            channel_id = rps_games[inter.guild_id][inter.author.id][1]
            channel = inter.guild.get_channel(channel_id) or inter.guild.get_thread(channel_id)
            if channel is not None:
                try:
                    await channel.fetch_message(rps_games[inter.guild_id][inter.author.id][0])
                    await inter.response.send_message("You already have a game in progress.", ephemeral=True)
                    return
                except disnake.NotFound:
                    del rps_games[inter.guild_id][inter.author.id]
        if bet > await get_balance(inter.guild_id, inter.author.id):
            await inter.response.send_message("You do not have enough money.", ephemeral=True)
            return
        if bet < 1:
            await inter.response.send_message("The bet must be at least 1.", ephemeral=True)
            return
        embed = disnake.Embed(
            description=f"Your current balance: ${await get_balance(inter.guild_id, inter.author.id)}\nBet: ${bet}",
            title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
        message = await inter.channel.send(embed=embed,
                                           view=RPSView(bet=bet, author=inter.author.id, guild=inter.guild_id,
                                                        channel=inter.channel_id))
        rps_games[inter.guild_id][inter.author.id] = [message.id, inter.channel_id]
        await inter.response.send_message("Successfully started a Rock Paper Scissors game.", ephemeral=True)


def setup(bot):
    bot.add_cog(Games(bot))
