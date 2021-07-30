import discord
from discord.ext.commands import command, Cog
from game import GameCog

cogs = ["Misc", "Game"]

class MiscCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def emojiname(self, ctx, emoji):
        await ctx.send(get_name(emoji))

    @command()
    async def mycolour(self, ctx):
        await ctx.send(ctx.author.colour)

    @command()
    async def name(self, ctx):
        await ctx.send(ctx.author.name)

    @command()
    async def nickname(self, ctx):
        await ctx.send(ctx.author.nick)

def get_name(s):
    return s.encode('ascii', 'namereplace')