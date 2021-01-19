import discord
from discord.ext.commands import command, Cog
from game import GameCog

cogs = ["Misc", "Game"]

class MiscCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def reload(self, ctx, *, cog: str = None):
        if cog:
            if (cog_name := cog.lower().capitalize()) in cogs:
                reloading = [cog_name]
            else:
                await ctx.send("cog not found")
                return False
        else:
            reloading = cogs.copy()
        for c in reloading:
            self.bot.remove_cog(c+"Cog")
            self.bot.add_cog(eval(c+"Cog(self.bot)"))
