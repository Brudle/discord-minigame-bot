import discord
from discord.ext.commands import command, group, Cog, Greedy
from game import games
from monopoly.game import MonopolyGame

class Monopoly(Cog):

    def __init__(self, bot):
        self.bot = bot

    def player_check(self, user):
        for game in games:
            if type(game) == MonopolyGame:
                for player in game.players:
                    if player.user == user:
                        return player, game
        return None, None

    @command()
    async def monopoly(self, ctx, users: Greedy[discord.Member]=None):
        game = MonopolyGame(ctx.channel, ctx.author)
        await game.update_lobby()
        games.append(game)
        if users:
            for user in users:
                await game.invite(user)

    @command()
    async def colour(self, ctx, colour: discord.Colour):
        player, game = self.player_check(ctx.author)
        if player:
            await game.chose_colour(player, colour)

    @command()
    async def bid(self, ctx, amount: int):
        player, game = self.player_check(ctx.author)
        if player:
            await game.bid(player, amount)

    @command()
    async def buy(self, ctx, improvement: str=None, group: str=None, property: str=None):
        player, game = self.player_check(ctx.author)
        if player:
            await player.buy(improvement, group, property)

    @command()
    async def sell(self, ctx, improvement: str=None, group: str=None, property: str=None):
        player, game = self.player_check(ctx.author)
        if player:
            await player.sell(improvement, group, property)

    @command()
    async def mortgage(self, ctx, property: int=None):
        player, game = self.player_check(ctx.author)
        if player:
            await player.mortgage(property)

    @command()
    async def unmortgage(self, ctx, property: int=None):
        player, game = self.player_check(ctx.author)
        if player:
            await player.unmortgage(property)

    @group()
    async def trade(self, ctx):
        pass

    @trade.command()
    async def start(self, ctx, user: discord.Member):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade(user)

    @trade.group()
    async def offer(self, ctx):
        pass

    @offer.command(aliases=["cash"])
    async def cash_offer(self, ctx, amount: int):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade_offer_cash(amount)

    @offer.group(aliases=["property"])
    async def property_offer(self, ctx):
        pass

    @property_offer.command(aliases=["add"])
    async def add_offer(self, ctx, property: int=None):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade_offer_add_property(property)

    @property_offer.command(aliases=["remove"])
    async def remove_offer(self, ctx, property: int=None):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade_offer_remove_property(property)

    @offer.command(aliases=["card"])
    async def card_offer(self, ctx, amount: int):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade_offer_card(amount)

    @trade.group()
    async def ask(self, ctx):
        pass

    @ask.command(aliases=["cash"])
    async def cash_ask(self, ctx, amount: int):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade_ask_cash(amount)

    @ask.group(aliases=["property"])
    async def property_ask(self, ctx):
        pass

    @property_ask.command(aliases=["add"])
    async def add_ask(self, ctx, property: int):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade_ask_add_property(property)

    @property_ask.command(aliases=["remove"])
    async def remove_ask(self, ctx, property: int):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade_ask_remove_property(property)

    @ask.command(aliases=["card"])
    async def card_ask(self, ctx, amount: int):
        player, game = self.player_check(ctx.author)
        if player:
            await player.trade_ask_card(amount)