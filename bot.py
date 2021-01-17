import discord
from discord.ext import commands
import game

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.emojis = True
intents.messages = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!bm ',  intents=intents)
bot.add_cog(game.GameCog(bot))

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

with open ("token.txt", "r") as token:
    bot.run(token.readline())
