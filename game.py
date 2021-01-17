import discord
from discord.ext.commands import command, Cog, Greedy

games = []

class Game:

    def __init__(self, channel, creator, game, maxplayers=None):
        self.channel = channel
        self.creator = creator
        self.game = game
        self.maxplayers = maxplayers
        self.players = {creator}
        self.invited = set()

    async def update_lobby(self):
        self.embed = discord.Embed(title=self.game, desription="test", colour=discord.Colour.green())
        self.embed.add_field(name="Players", value="\n".join([p.name for p in self.players]), inline=True)
        self.embed.add_field(name="Invited", value=("\n".join([p.name for p in self.invited]) or "---"), inline=True)
        try:
            await self.lobby.edit(embed=self.embed)
        except AttributeError:
            self.lobby = await self.channel.send(embed=self.embed)
        await self.lobby.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await self.lobby.add_reaction("\N{CROSS MARK}")
        print(self.lobby)

    async def invite(self, player):
        self.invited.add(player)
        await self.update_lobby()

    async def accept_invite(self, player):
        self.invited.remove(player)
        self.players.add(player)
        await self.channel.send("{} accepted the invite".format(player.name))
        await self.update_lobby()

    async def decline_invite(self, player):
        self.invited.remove(player)
        await self.channel.send("{} declined the invite".format(player.name))
        await self.update_lobby()

    async def start(self):
        await self.channel.send("game starting")
        await self.lobby.delete()

    async def cancel(self):
        await self.channel.send("game cancelled")
        await self.lobby.delete()

class GameCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user != self.bot.user:
            for game in games:
                if game.lobby == reaction.message:
                    if user == game.creator:
                        if reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
                            await game.start()
                        elif reaction.emoji == "\N{CROSS MARK}":
                            await game.cancel()
                        else:
                            await reaction.remove(user)
                    elif user in game.invited:
                        if reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
                            await game.accept_invite(user)
                        elif reaction.emoji == "\N{CROSS MARK}":
                            await game.decline_invite(user)

    @command()
    async def game(self, ctx, *, gamename="none"):
        game = Game(ctx.channel, ctx.author, gamename)
        games.append(game)
        await game.update_lobby()

    @command()
    async def invite(self, ctx, users: Greedy[discord.Member]):
        for game in games:
            if game.creator == ctx.author:
                for user in users:
                    if user not in game.players:
                        await game.invite(user)
                        await game.update_lobby()

    @command()
    async def accept(self, ctx):
        for game in games:
            if player := ctx.author in game.invited:
                await game.accept_invite(player)

    @command()
    async def decline(self, ctx):
        for game in games:
            if player := ctx.author in game.invited:
                await game.decline_invite(player)
