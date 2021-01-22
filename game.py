import discord
import traceback
from discord.ext.commands import command, Cog, Greedy

games = []
emojis = {}
emojis["tick"] = "\N{WHITE HEAVY CHECK MARK}"
emojis["cross"] = "\N{CROSS MARK}"

class Game:

    def __init__(self, channel, creator, game, maxplayers=None):
        self.bot = bot
        self.channel = channel
        self.creator = creator
        self.game = game
        self.maxplayers = maxplayers
        self.players = {creator}
        self.invited = set()
        self.declined = set()

    async def update_lobby(self):
        self.embed = discord.Embed(title=self.game,
        description="invitation response can be changed any number of times",
        colour=discord.Colour.green())
        self.embed.add_field(name="Players", value="\n".join([p.name for p in self.players]), inline=True)
        if self.invited:
            self.embed.add_field(name="Invited", value=("\n".join([p.name for p in self.invited])), inline=True)
        if self.declined:
            self.embed.add_field(name="Declined", value=("\n".join([p.name for p in self.declined])), inline=True)
        self.embed.add_field(name="Creator Commands", value=(
        "```{0}invite <user(s)>\n"
        "{0}kick   <user(s)>```"
        ).format("!bm "), inline=False)
        space = "\u200b    "
        self.embed.add_field(name="Reaction", value=(
        emojis["tick"]+"\n"+\
        emojis["cross"]), inline=True)
        self.embed.add_field(name="Creator", value=(
        "start the game\n"
        "cancel the game"), inline=True)
        self.embed.add_field(name="Invitee", value=(
        "accept an invite\n"
        "decline an invite"), inline=True)
        try:
            await self.lobby.edit(embed=self.embed)
        except AttributeError:
            self.lobby = await self.channel.send(embed=self.embed)
        await self.lobby.add_reaction(emojis["tick"])
        await self.lobby.add_reaction(emojis["cross"])

    async def invite(self, player):
        if player in self.players:
            await self.channel.send("{} has already accepted an invite!".format(player.name))
        elif player in self.invited:
            await self.channel.send("{} has already been invited".format(player.name))
        elif player in self.declined:
            await self.channel.send("{} has already declined the invite".format(player.name))
        else:
            self.invited.add(player)
            await self.update_lobby()

    async def accept_invite(self, player):
        self.invited.remove(player)
        self.players.add(player)
        await self.update_lobby()

    async def undo_accept(self, player):
        if player in self.players:
            self.players.remove(player)
            self.invited.add(player)
            await self.update_lobby()

    async def decline_invite(self, player):
        self.invited.remove(player)
        self.declined.add(player)
        await self.update_lobby()

    async def undo_decline(self, player):
        if player in self.declined:
            self.declined.remove(player)
            self.invited.add(player)
            await self.update_lobby()

    async def kick(self, player):
        if player in self.players:
            self.players.remove(player)
        elif player in self.invited:
            self.invited.remove(player)
        elif player in self.declined:
            self.declined.remove(player)
        else:
            return False
        await self.update_lobby()

    async def start(self):
        await self.channel.send("game starting")

    async def cancel(self):
        await self.channel.send("game cancelled")

class GameCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user != self.bot.user:
            for game in games:
                if game.lobby == reaction.message:
                    if user == game.creator:
                        if reaction.emoji == emojis["tick"]:
                            await game.start()
                        elif reaction.emoji == emojis["cross"]:
                            await game.cancel()
                    elif user in game.invited:
                        if reaction.emoji == emojis["tick"]:
                            await game.accept_invite(user)
                        elif reaction.emoji == emojis["cross"]:
                            await game.decline_invite(user)

    async def cog_command_error(self, ctx, error):
        print(ctx)
        traceback.print_exc()

    @Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user != self.bot.user:
            for game in games:
                if game.lobby == reaction.message:
                    if reaction.emoji == emojis["tick"]:
                        await game.undo_accept(user)
                    elif reaction.emoji == emojis["cross"]:
                        await game.undo_decline(user)

    @command()
    async def game(self, ctx, gamename, users: Greedy[discord.Member]=None):
        game = Game(ctx.channel, ctx.author, gamename)
        await game.update_lobby()
        games.append(game)
        if users:
            for user in users:
                await game.invite(user)

    @command()
    async def invite(self, ctx, users: Greedy[discord.Member]):
        if users:
            for game in games:
                if game.creator == ctx.author:
                    for user in users:
                        await game.invite(user)

    @command()
    async def kick(self, ctx, users: Greedy[discord.Member]):
        if users:
            for game in games:
                if game.creator == ctx.author:
                    for user in users:
                        await game.kick(user)
