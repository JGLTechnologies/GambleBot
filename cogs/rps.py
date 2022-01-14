import random
import time
from db import set_balance, get_balance
import disnake
from disnake.ext import commands
from collections import defaultdict
import asyncio

rps_games = defaultdict(lambda: {})


class RPSMenu(disnake.ui.Select):
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
        if bal <= 0:
            await inter.channel.send("You are out of money.", delete_after=7)
            try:
                msg = await inter.channel.fetch_message(rps_games[inter.guild_id][self.view.author][0])
                await msg.delete()
            except Exception:
                pass
            return
        if self.view.rps.bet > bal:
            self.bet = bal
        player_choice = self.values[0].lower()
        computer_choice = random.choice(["rock", "paper", "scissors"])
        if player_choice == computer_choice:
            embed = disnake.Embed(
                description=f"It's a tie!\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
        elif player_choice == "rock" and computer_choice == "scissors":
            bal += self.bet
            embed = disnake.Embed(
                description=f"You won!\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
            await set_balance(inter.guild_id, inter.author.id, bal)
        elif player_choice == "paper" and computer_choice == "rock":
            bal += self.bet
            embed = disnake.Embed(
                description=f"You won!\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
            await set_balance(inter.guild_id, inter.author.id, bal)
        elif player_choice == "scissors" and computer_choice == "paper":
            bal += self.bet
            embed = disnake.Embed(
                description=f"You won!\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>",
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
                description=f"You lost!\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>",
                title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
            await set_balance(inter.guild_id, inter.author.id, bal)
        await inter.response.edit_message(embed=embed)


class ChangeBet(disnake.ui.Button):
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        await inter.response.defer()
        bal = await get_balance(inter.guild_id, inter.author.id)
        msg = await inter.channel.send("Please type a bet in the chat.")
        try:
            message = await self.view.bot.wait_for('message',
                                                check=lambda message: message.author.id == inter.author.id,
                                                timeout=30)
            await message.delete()
            bet = round(float(message.content), 2)
        except asyncio.TimeoutError:
            await inter.followup.send("You took too long to type a bet.", ephemeral=True)
            await msg.delete()
            return
        except ValueError:
            await msg.delete()
            await inter.followup.send("That bet is not a valid number.", ephemeral=True)
            return
        await msg.delete()
        if bet > bal:
            await msg.delete()
            await inter.followup.send("You do not have enough money.", ephemeral=True)
            return
        self.view.rps.bet = bet
        embed = disnake.Embed(
            description=f"Your current balance: ${bal}\nBet: ${self.view.rps.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>",
            title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
        await inter.message.edit(embed=embed)


class RPSView(disnake.ui.View):
    def __init__(self, bet: int, author: int, guild: int, channel: int, bot: commands.AutoShardedInteractionBot):
        super().__init__(timeout=3600)
        self.bot = bot
        self.author = author
        self.channel = channel
        self.guild = guild
        self.rps = RPSMenu(bet)
        self.change_bet = ChangeBet(label="Change Bet", style=disnake.ButtonStyle.blurple)
        self.add_item(self.change_bet)
        self.add_item(self.rps)

    async def on_timeout(self) -> None:
        try:
            msg = await self.bot.get_channel(self.channel).fetch_message(rps_games[self.guild][self.author][0])
            await msg.delete()
        except Exception:
            pass
        try:
            del rps_games[self.guild][self.author]
        except KeyError:
            pass
        try:
            await self.bot.get_channel(self.channel).send(
                f"{self.bot.get_guild(self.guild).get_member(self.author).mention}, your Rock Paper Scissors game has expired. Start a new one by doing `/rps`")
        except Exception:
            pass


class RPS(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot

    @commands.slash_command(name="rps")
    async def rock_paper_scissors(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @rock_paper_scissors.sub_command(name="start")
    async def start(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
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
        msg = await inter.channel.send("Please type a bet in the chat.")
        try:
            message = await self.bot.wait_for('message',
                                               check=lambda message: message.author.id == inter.author.id,
                                               timeout=30)
            await message.delete()
            bet = round(float(message.content), 2)
        except asyncio.TimeoutError:
            await inter.followup.send("You took too long to type a bet.", ephemeral=True)
            await msg.delete()
            return
        except ValueError:
            await msg.delete()
            await inter.followup.send("That bet is not a valid number.", ephemeral=True)
            return
        await msg.delete()
        if bet > await get_balance(inter.guild_id, inter.author.id):
            await inter.followup.send("You do not have enough money.", ephemeral=True)
            return
        if bet < 1:
            await inter.followup.send("The bet must be at least 1.", ephemeral=True)
            return
        view = RPSView(bet=bet, author=inter.author.id, guild=inter.guild_id,
                       channel=inter.channel_id, bot=self.bot)
        view.started_at = time.time()
        embed = disnake.Embed(
            description=f"Your current balance: ${await get_balance(inter.guild_id, inter.author.id)}\nBet: ${bet}\nGame Expires: <t:{round(view.started_at + 3600)}:R>",
            title=f"{str(inter.author)}'s Rock Paper Scissors Game", color=disnake.Color.blurple())
        message = await inter.channel.send(inter.author.mention, embed=embed,
                                           view=view)
        rps_games[inter.guild_id][inter.author.id] = [message.id, inter.channel_id, view]
        await inter.followup.send("Successfully started a Rock Paper Scissors game.", ephemeral=True)

    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    @rock_paper_scissors.sub_command(name="cancel")
    async def cancel(self, inter: disnake.ApplicationCommandInteraction):
        try:
            rps_games[inter.guild_id][inter.author.id]
        except KeyError:
            await inter.response.send_message("You do not have a Rock Paper Scissors game in progress.", ephemeral=True)
            return
        rps_games[inter.guild_id][inter.author.id][2].stop()
        del rps_games[inter.guild_id][inter.author.id]
        await inter.response.send_message("Successfully canceled your Rock Paper Scissors game.", ephemeral=True)


def setup(bot):
    bot.add_cog(RPS(bot))
