import asyncio
import random
import time
from db import set_balance, get_balance
import disnake
from disnake.ext import commands
from collections import defaultdict

blackjack_games = defaultdict(lambda: {})


class PlayAgain(disnake.ui.Button):
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        bal = await get_balance(inter.guild_id, inter.author.id)
        if bal <= 0:
            await inter.channel.send("You are out of money.", delete_after=7)
            try:
                msg = await inter.channel.fetch_message(blackjack_games[inter.guild_id][self.view.author][0])
                await msg.delete()
            except Exception:
                pass
            return
        if self.view.rps.bet > bal:
            self.view.bet = bal


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
            try:
                bet = int(message.content)
            except ValueError:
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
            await inter.followup.send("You do not have enough money.", ephemeral=True)
            return
        self.view.rps.bet = bet
        embed = disnake.Embed(
            description=f"Your current balance: ${bal}\nBet: ${self.view.rps.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>",
            title=f"{str(inter.author)}'s Blackjack Game", color=disnake.Color.blurple())
        await inter.message.edit(embed=embed)


class BlackJackView(disnake.ui.View):
    def __init__(self, bet: int, author: int, guild: int, channel: int, bot: commands.AutoShardedInteractionBot):
        super().__init__(timeout=3600)
        self.author = author
        self.bot = bot
        self.channel = channel
        self.guild = guild
        self.bet = bet
        self.play_again = PlayAgain(label="Play Again", style=disnake.ButtonStyle.blurple)
        self.add_item(self.play_again)

    async def on_timeout(self) -> None:
        try:
            msg = await self.bot.get_channel(self.channel).fetch_message(blackjack_games[self.guild][self.author][0])
            await msg.delete()
        except Exception:
            pass
        try:
            del blackjack_games[self.guild][self.author]
        except KeyError:
            pass
        try:
            await self.bot.get_channel(self.channel).send(
                f"{self.bot.get_guild(self.guild).get_member(self.author).mention}, your Blackjack game has expired. "
                "Start a new one by doing `/blackjack start`")
        except Exception:
            pass


class BlackJack(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot

    @commands.slash_command(name="blackjack")
    async def blackjack(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @blackjack.sub_command(name="start")
    async def start(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        if inter.author.id in blackjack_games[inter.guild_id]:
            channel_id = blackjack_games[inter.guild_id][inter.author.id][1]
            channel = inter.guild.get_channel(channel_id) or inter.guild.get_thread(channel_id)
            if channel is not None:
                try:
                    await channel.fetch_message(blackjack_games[inter.guild_id][inter.author.id][0])
                    await inter.response.send_message("You already have a game in progress.", ephemeral=True)
                    return
                except disnake.NotFound:
                    del blackjack_games[inter.guild_id][inter.author.id]
        msg = await inter.channel.send("Please type a bet in the chat.")
        try:
            message = (await self.bot.wait_for('message',
                                               check=lambda message: message.author.id == inter.author.id,
                                               timeout=30))
            await message.delete()
            try:
                bet = int(message.content)
            except ValueError:
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
        view = BlackJackView(bet=bet, author=inter.author.id, guild=inter.guild_id,
                             channel=inter.channel_id, bot=self.bot)
        view.started_at = time.time()
        embed = disnake.Embed(
            description=f"Your current balance: ${await get_balance(inter.guild_id, inter.author.id)}\nBet: ${bet}\nGame Expires: <t:{round(view.started_at + 3600)}:R>",
            title=f"{str(inter.author)}'s Blackjack Game", color=disnake.Color.blurple())
        message = await inter.channel.send(embed=embed,
                                           view=view)
        blackjack_games[inter.guild_id][inter.author.id] = [message.id, inter.channel_id, view]
        await inter.followup.send("Successfully started a Blackjack game.", ephemeral=True)

    @commands.guild_only()
    @commands.bot_has_permissions(administrator=True)
    @blackjack.sub_command(name="cancel")
    async def cancel(self, inter: disnake.ApplicationCommandInteraction):
        try:
            blackjack_games[inter.guild_id][inter.author.id]
        except KeyError:
            await inter.response.send_message("You do not have a Blackjack game in progress.", ephemeral=True)
            return
        blackjack_games[inter.guild_id][inter.author.id][2].stop()
        del blackjack_games[inter.guild_id][inter.author.id]
        await inter.response.send_message("Successfully canceled your Blackjack game.", ephemeral=True)


def setup(bot):
    bot.add_cog(BlackJack(bot))
