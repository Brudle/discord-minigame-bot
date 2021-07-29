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

def get_name(s):
    return s.encode('ascii', 'namereplace')