import discord
import traceback
from discord.ext.commands import command, Cog, Greedy

games = []
emojis = {}
emojis["tick"] = "\N{WHITE HEAVY CHECK MARK}"
emojis["cross"] = "\N{CROSS MARK}"

class Game:

    def __init__(self, name, channel, creator, minplayers=None, maxplayers=None):
        self.name = name
        self.channel = channel
        self.creator = creator
        self.minplayers = minplayers
        self.maxplayers = maxplayers
        self.players = {creator}
        self.invited = set()
        self.declined = set()
        self.reaction_messages = []
        self.reaction_message = None
        self.lobby_done = False

    async def update_lobby(self):
        embed = discord.Embed(title=f"{self.name} Lobby",
        description="invitation response can be changed any number of times",
        colour=discord.Colour.green())
        embed.add_field(name="Players", value="\n".join([p.name for p in self.players]), inline=True)
        if self.invited:
            embed.add_field(name="Invited", value=("\n".join([p.name for p in self.invited])), inline=True)
        if self.declined:
            embed.add_field(name="Declined", value=("\n".join([p.name for p in self.declined])), inline=True)
        embed.add_field(name="Creator Commands", value=(
        "```{0}invite <user(s)>\n"
        "{0}kick   <user(s)>```"
        ).format("!bm "), inline=False)
        space = "\u200b    "
        embed.add_field(name="Reaction", value=(
        emojis["tick"]+"\n"+\
        emojis["cross"]), inline=True)
        embed.add_field(name="Creator", value=(
        "start the game\n"
        "cancel the game"), inline=True)
        embed.add_field(name="Invitee", value=(
        "accept an invite\n"
        "decline an invite"), inline=True)
        try:
            await self.lobby.edit(embed=embed)
        except AttributeError:
            self.lobby = await self.channel.send(embed=embed)
        await self.lobby.add_reaction(emojis["tick"])
        await self.lobby.add_reaction(emojis["cross"])
        self.reaction_messages.append(self.lobby)

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
        if len(self.players) < self.minplayers:
            await self.channel.send("not enough players")
        elif len(self.players) > self.maxplayers:
            await self.channel.send("too many players")
        else:
            await self.channel.send("game starting")
            self.lobby_done = True
            await self.play()

    async def cancel(self):
        self.lobby_done = True
        await self.channel.send("game cancelled")

    async def create_reaction_message(self, embed: discord.Embed, reactions: dict):
        embed.add_field(name="Reaction", value="\n".join(reactions.keys()))
        embed.add_field(name="Action", value="\n".join(r[1] for r in reactions.values()))
        message = await self.channel.send(embed=embed)
        for reaction in reactions:
            await message.add_reaction(reaction)
        self.reactions = {r: reactions[r][0] for r in reactions}
        self.reaction_message = message

class Player:

    def __init__(self, user: discord.Member, game: Game):
        self.user = user
        self.game = game
        self.name = self.user.nick or self.user.name
        self.colour = discord.Colour.default()

    def set_colour(self, colour: discord.Colour):
        self.colour = colour

    async def send_as_author(self, embed: discord.Embed, file: discord.File=None) -> discord.Message:
        embed.colour = self.colour
        embed.set_author(name=self.name, icon_url=self.user.avatar_url)
        return await self.game.channel.send(embed=embed, file=file)

    async def create_reaction_message(self, embed: discord.Embed, reactions, file: discord.File=None):
        embed.add_field(name="React", value="\n".join(reactions.keys()))
        embed.add_field(name="Action", value="\n".join(r[1] for r in reactions.values()))
        message = await self.send_as_author(embed, file)
        for reaction in reactions:
            await message.add_reaction(reaction)
        self.reaction_message = message
        self.reactions = {r: reactions[r][1] for r in reactions}

class GameCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user != self.bot.user:
            for game in games:
                if reaction.message == game.lobby and not game.lobby_done:
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
                elif reaction.message in game.reaction_messages:
                    await game.reaction_add(reaction, user)
                else:
                    for player in game.players:
                        if player.user == user:
                            if game.reaction_message == reaction.message and reaction.emoji in game.reactions:
                                await game.reactions(reaction.emoji)(player)
                            elif player.reaction_message == reaction.message and reaction.emoji in player.reactions:
                                await player.reactions(reaction.emoji)

    @Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user != self.bot.user:
            for game in games:
                if reaction.message in game.reaction_messages:
                    await game.reaction_remove(reaction, user)
                elif reaction.message == game.lobby and not game.lobby_done:
                    if reaction.emoji == emojis["tick"]:
                        await game.undo_accept(user)
                    elif reaction.emoji == emojis["cross"]:
                        await game.undo_decline(user)

    async def cog_command_error(self, ctx, error):
        print(ctx)
        traceback.print_exc()

    @command()
    async def invite(self, ctx, users: Greedy[discord.Member]):
        if users:
            for game in games:
                if game.creator == ctx.author and not game.lobby_done:
                    for user in users:
                        await game.invite(user)

    @command()
    async def kick(self, ctx, users: Greedy[discord.Member]):
        if users:
            for game in games:
                if game.creator == ctx.author and not game.lobby_done:
                    for user in users:
                        await game.kick(user)
