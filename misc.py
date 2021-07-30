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

    @command()
    async def POStest(self, ctx, user: discord.Member):
        """
        testing testing 1 2 3
        does this show in the help command hmm i wonder
        """
        if "Brudle" in user.name:
            await ctx.send(f"{user.mention} is not a POS")
        else:
            await ctx.send(f"{user.mention} is a certified POS")

    @command()
    async def noncetest(self, ctx, user: discord.Member):
        "backed by the national police database"
        if "Brudle" in user.name or "ACivil" in user.name or "Genocide" in user.name or "Kounter" in user.name or "Moby" in user.name or "Kᴀᴢɪ" in user.name or "Owner" in user.name:
            await ctx.send(f"{user.mention} is safe to be around your children")
        else:
            await ctx.send(f"{user.mention} is definitely a nonce")

def get_name(s):
    return s.encode('ascii', 'namereplace')