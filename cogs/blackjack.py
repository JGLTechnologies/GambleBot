import asyncio
import random
import time
import typing
from db import set_balance, get_balance
import disnake
from disnake.ext import commands
from collections import defaultdict

blackjack_games = defaultdict(lambda: {})
symbols = ["♣", "❤", "♠", "♦"]
second_items = {}


class PlayAgain(disnake.ui.Button):
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        if self.view.pa_lock.locked():
            return
        async with self.view.pa_lock:
            if self.view.game:
                await inter.response.send_message("you are already playing a game.")
                return
            await self.view.start_game(inter)


class Stand(disnake.ui.Button):
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        if self.view.stand_lock.locked():
            return
        async with self.view.stand_lock:
            if not self.view.game:
                return
            await self.view.stand(inter)


class Hit(disnake.ui.Button):
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        if self.view.hit_lock.locked():
            return
        async with self.view.hit_lock:
            if not self.view.game:
                return
            card = random.choice(self.view.deck)
            self.view.deck.remove(card)
            self.view.player.append(f"{random.choice(symbols)} {card}")
            dealer = 0
            player = 0
            bal = await get_balance(inter.guild_id, inter.author.id)
            if self.view.bet > bal:
                self.view.bet = bal
            for card in self.view.dealer:
                symbol, num = card.split(" ")
                if num == "A":
                    if self.view.get_num(self.view.dealer) + 11 > 21:
                        dealer += 1
                        break
                    else:
                        dealer += 11
                        break
                if num in ["J", "Q", "K"]:
                    dealer += 10
                else:
                    dealer += int(num)
                break
            for card in self.view.player:
                symbol, num = card.split(" ")
                if num == "A":
                    if self.view.get_num(self.view.player) + 11 > 21:
                        player += 1
                        continue
                    else:
                        player += 11
                        continue
                if num in ["J", "Q", "K"]:
                    player += 10
                else:
                    player += int(num)
            player_string = ""
            dealer_string = ""
            for card in self.view.player:
                symbol, num = card.split(" ")
                player_string += f"[{symbol} {num}] "
            for card in self.view.dealer:
                symbol, num = card.split(" ")
                dealer_string += f"[{symbol} {num}] "
                break
            embed = disnake.Embed(color=disnake.Color.blurple(),
                                  title=f"{str(inter.author)}'s Blackjack Game")
            if player > 21:
                bal = round(bal - self.view.bet, 2)
                await set_balance(inter.guild_id, inter.author.id, bal)
                embed.description = f"**You Busted!**\nYour current balance: ${bal}\nBet: ${self.view.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>"
                self.view.add_item(self.view.play_again)
                self.view.add_item(self.view.change_bet)
                self.view.game = False
                self.view.remove_item(self)
                self.view.remove_item(self.view.stand_button)
            elif player == 21:
                await self.view.stand(inter)
                return
            else:
                embed.description = f"Your current balance: ${bal}\nBet: ${self.view.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>"
            embed.add_field(inline=False, name=f"Dealer's Hand ({dealer})", value=dealer_string)
            embed.add_field(inline=False, name=f"{str(inter.author)}'s Hand ({player})", value=player_string)
            await inter.response.edit_message(embed=embed, view=self.view)


class ChangeBet(disnake.ui.Button):
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author:
            return
        if self.view.bet_lock.locked():
            return
        async with self.view.bet_lock:
            if self.view.game:
                await inter.response.send_message("You cannot change your bet when there is a game in progress.")
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
            self.view.bet = bet
            embed = disnake.Embed(
                description=f"Your current balance: ${bal}\nBet: ${self.view.bet}\nGame Expires: <t:{round(self.view.started_at + 3600)}:R>",
                title=f"{str(inter.author)}'s Blackjack Game", color=disnake.Color.blurple())
            try:
                await inter.message.edit(embed=embed)
            except:
                try:
                    blackjack_games[inter.guild_id][inter.author.id][2].stop()
                except:
                    pass
                return


class BlackJackView(disnake.ui.View):
    def __init__(self, bet: int, author: int, guild: int, channel: int, bot: commands.AutoShardedInteractionBot):
        super().__init__(timeout=3600)
        self.author = author
        self.bot = bot
        self.channel = channel
        self.guild = guild
        self.bet = bet
        self.started_at = time.time()
        self.play_again = PlayAgain(label="Play Again", style=disnake.ButtonStyle.blurple)
        self.change_bet = ChangeBet(label="Change Bet", style=disnake.ButtonStyle.red)
        self.hit = Hit(label="Hit", style=disnake.ButtonStyle.green)
        self.stand_button = Stand(label="Stand", style=disnake.ButtonStyle.red)
        self.player = None
        self.dealer = None
        self.game = True
        self.deck = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "K", "Q", "J"] * 24
        self.stand_lock = asyncio.Semaphore(1)
        self.hit_lock = asyncio.Semaphore(1)
        self.pa_lock = asyncio.Semaphore(1)
        self.bet_lock = asyncio.Semaphore(1)

    def generate_deck(self):
        self.deck = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "K", "Q", "J"] * 24

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

    def get_num(self, cards: list) -> int:
        num = 0
        cards = [card.split(" ")[1] for card in cards if card.split(" ")[1] != "A"]
        for card in cards:
            if card in ["J", "K", "Q"]:
                num += 10
            else:
                num += int(card)
        return num

    async def start_game(self, msg: typing.Union[disnake.Message, disnake.MessageInteraction]) -> None:
        self.game = True
        self.add_item(self.stand_button)
        self.add_item(self.hit)
        self.remove_item(self.play_again)
        self.remove_item(self.change_bet)
        member = self.bot.get_guild(self.guild).get_member(self.author)
        if len(self.deck) < 52:
            self.generate_deck()
        dealer_card_1 = random.choice(self.deck)
        dealer_card_2 = random.choice(self.deck)
        player_card_1 = random.choice(self.deck)
        player_card_2 = random.choice(self.deck)
        for card in [dealer_card_1, dealer_card_2, player_card_1, player_card_2]:
            self.deck.remove(card)
        self.dealer = [f"{random.choice(symbols)} {dealer_card_1}",
                       f"{random.choice(symbols)} {dealer_card_2}"]
        self.player = [f"{random.choice(symbols)} {player_card_1}",
                       f"{random.choice(symbols)} {player_card_2}"]
        dealer = 0
        player = 0
        player_string = ""
        dealer_string = ""
        bal = await get_balance(self.guild, self.author)
        if self.bet > bal:
            self.bet = bal
        embed = disnake.Embed(color=disnake.Color.blurple(),
                              title=f"{str(member)}'s Blackjack Game",
                              description=f"Your current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>")
        for card in self.dealer:
            symbol, num = card.split(" ")
            if num == "A":
                if self.get_num(self.dealer) + 11 > 21:
                    dealer += 1
                    continue
                else:
                    dealer += 11
                    continue
            if num in ["J", "Q", "K"]:
                dealer += 10
            else:
                dealer += int(num)
        for card in self.player:
            symbol, num = card.split(" ")
            if num == "A":
                if self.get_num(self.player) + 11 > 21:
                    player += 1
                    continue
                else:
                    player += 11
                    continue
            if num in ["J", "Q", "K"]:
                player += 10
            else:
                player += int(num)
        if dealer == 21 and player != 21:
            self.add_item(self.play_again)
            self.add_item(self.change_bet)
            self.remove_item(self.stand_button)
            self.remove_item(self.hit)
            self.game = False
            bal = round(bal - self.bet, 2)
            await set_balance(self.guild, self.author, bal)
            embed.description = f"**The dealer got a Blackjack. You lost!**\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>"
            for card in self.dealer:
                symbol, num = card.split(" ")
                dealer_string += f"[{symbol} {num}] "
        elif player == 21 and dealer == 21:
            self.add_item(self.play_again)
            self.add_item(self.change_bet)
            self.remove_item(self.stand_button)
            self.remove_item(self.hit)
            self.game = False
            embed.description = f"**It's a push!**\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>"
            for card in self.dealer:
                symbol, num = card.split(" ")
                dealer_string += f"[{symbol} {num}] "
        elif player == 21 and dealer != 21:
            self.add_item(self.play_again)
            self.add_item(self.change_bet)
            self.remove_item(self.stand_button)
            self.remove_item(self.hit)
            self.game = False
            embed.description = f"**You got a Blackjack. You won!**\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>"
            for card in self.dealer:
                symbol, num = card.split(" ")
                dealer_string += f"[{symbol} {num}] "
        else:
            for card in self.dealer:
                symbol, num = card.split(" ")
                dealer_string += f"[{symbol} {num}] "
                break
            dealer = 0
            for card in self.dealer:
                symbol, num = card.split(" ")
                if num == "A":
                    if self.get_num(self.dealer) + 11 > 21:
                        dealer += 1
                        break
                    else:
                        dealer += 11
                        break
                if num in ["J", "Q", "K"]:
                    dealer += 10
                else:
                    dealer += int(num)
                break
        for card in self.player:
            symbol, num = card.split(" ")
            player_string += f"[{symbol} {num}] "
        embed.add_field(inline=False, name=f"Dealer's Hand ({dealer})", value=dealer_string)
        embed.add_field(inline=False, name=f"{str(member)}'s Hand ({player})", value=player_string)
        if isinstance(msg, disnake.MessageInteraction):
            await msg.response.edit_message(embed=embed, view=self)
        else:
            try:
                await msg.edit(embed=embed, view=self)
            except:
                try:
                    blackjack_games[msg.guild.id][msg.author.id][2].stop()
                except:
                    pass
                return

    async def stand(self, inter: disnake.MessageInteraction):
        dealer = 0
        player = 0
        await inter.response.edit_message()
        bal = await get_balance(inter.guild_id, inter.author.id)
        if self.bet > bal:
            self.bet = bal
        for card in self.dealer:
            symbol, num = card.split(" ")
            if num == "A":
                if self.get_num(self.dealer) + 11 > 21:
                    dealer += 1
                    continue
                else:
                    dealer += 11
                    continue
            if num in ["J", "Q", "K"]:
                dealer += 10
            else:
                dealer += int(num)
        for card in self.player:
            symbol, num = card.split(" ")
            if num == "A":
                if self.get_num(self.player) + 11 > 21:
                    player += 1
                    continue
                else:
                    player += 11
                    continue
            if num in ["J", "Q", "K"]:
                player += 10
            else:
                player += int(num)
        player_string = ""
        for card in self.player:
            symbol, num = card.split(" ")
            player_string += f"[{symbol} {num}] "
        embed = disnake.Embed(
            description=f"Your current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>",
            color=disnake.Color.blurple(), title=f"{str(inter.author)}'s Blackjack Game")
        while dealer < 17:
            await asyncio.sleep(1)
            dealer = 0
            dealer_string = ""
            embed.clear_fields()
            card = random.choice(self.deck)
            self.deck.remove(card)
            self.dealer.append(f"{random.choice(symbols)} {card}")
            for card in self.dealer:
                symbol, num = card.split(" ")
                if num == "A":
                    if self.get_num(self.dealer) + 11 > 21:
                        dealer += 1
                        continue
                    else:
                        dealer += 11
                        continue
                if num in ["J", "Q", "K"]:
                    dealer += 10
                else:
                    dealer += int(num)
            for card in self.dealer:
                symbol, num = card.split(" ")
                dealer_string += f"[{symbol} {num}] "
            embed.add_field(inline=False, name=f"Dealer's Hand ({dealer})", value=dealer_string)
            embed.add_field(inline=False, name=f"{str(inter.author)}'s Hand ({player})", value=player_string)
            try:
                await inter.message.edit(embed=embed)
            except:
                try:
                    blackjack_games[inter.guild_id][inter.author.id][2].stop()
                except:
                    pass
                return
        dealer_string = ""
        for card in self.dealer:
            symbol, num = card.split(" ")
            dealer_string += f"[{symbol} {num}] "
        embed.clear_fields()
        embed.add_field(inline=False, name=f"Dealer's Hand ({dealer})", value=dealer_string)
        embed.add_field(inline=False, name=f"{str(inter.author)}'s Hand ({player})", value=player_string)
        if dealer == player:
            self.add_item(self.play_again)
            self.add_item(self.change_bet)
            self.remove_item(self.stand_button)
            self.remove_item(self.hit)
            self.game = False
            embed.description = f"**It's a push!**\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>"
        elif dealer > 21:
            bal = round(bal + self.bet, 2)
            await set_balance(inter.guild_id, inter.author.id, bal)
            self.add_item(self.play_again)
            self.add_item(self.change_bet)
            self.remove_item(self.stand_button)
            self.remove_item(self.hit)
            self.game = False
            embed.description = f"**The dealer busted. You won!**\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>"
        elif dealer > player:
            bal = round(bal - self.bet, 2)
            await set_balance(inter.guild_id, inter.author.id, bal)
            self.add_item(self.play_again)
            self.add_item(self.change_bet)
            self.remove_item(self.stand_button)
            self.remove_item(self.hit)
            self.game = False
            embed.description = f"**You lost!**\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>"
        else:
            bal = round(bal + self.bet, 2)
            await set_balance(inter.guild_id, inter.author.id, bal)
            self.add_item(self.play_again)
            self.add_item(self.change_bet)
            self.remove_item(self.stand_button)
            self.remove_item(self.hit)
            self.game = False
            embed.description = f"**You won!**\nYour current balance: ${bal}\nBet: ${self.bet}\nGame Expires: <t:{round(self.started_at + 3600)}:R>"
        try:
            await inter.message.edit(embed=embed, view=self)
        except:
            try:
                blackjack_games[inter.guild_id][inter.author.id][2].stop()
            except:
                pass
            return


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
        await inter.response.defer(ephemeral=True)
        msg = await inter.channel.send("Please type a bet in the chat.")
        try:
            message = await self.bot.wait_for('message',
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
        if bet > await get_balance(inter.guild_id, inter.author.id):
            await inter.followup.send("You do not have enough money.", ephemeral=True)
            return
        if bet < 1:
            await inter.followup.send("The bet must be at least 1.", ephemeral=True)
            return
        view = BlackJackView(bet=bet, author=inter.author.id, guild=inter.guild_id,
                             channel=inter.channel_id, bot=self.bot)
        embed = disnake.Embed(
            description=f"Your current balance: ${await get_balance(inter.guild_id, inter.author.id)}\nBet: ${bet}\nGame Expires: <t:{round(view.started_at + 3600)}:R>",
            title=f"{str(inter.author)}'s Blackjack Game", color=disnake.Color.blurple())
        message = await inter.channel.send(embed=embed,
                                           view=view)
        blackjack_games[inter.guild_id][inter.author.id] = [message.id, inter.channel_id, view]
        await view.start_game(message)
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
