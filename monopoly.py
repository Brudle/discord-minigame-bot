import asyncio
import discord
from discord.ext.commands import command, Cog, Greedy
import random
import collections
from game import Game, games
import asyncio
from PIL import Image, ImageDraw, ImageColor
import io

class MonopolyGame(Game):

    def __init__(self, *args):
        super().__init__(*args, minplayers=2, maxplayers=6)
        self.board = MonopolyBoard(self)
        self.monopoly_players = []
        self.choosing_colours = False
        self.deciding_order = False
        self.turn = 0
        self.current_turn = None

        self.properties = {}

        with open("properties.txt", "r") as file:

            property_txt = file.readlines()

        for i in range(28):

            square = int(property_txt[i*6].strip())
            name = property_txt[i*6+1].strip()
            price = int(property_txt[i*6+2].strip())
            rent = [int(x) for x in property_txt[i*6+3].strip().split(".")]
            group = property_txt[i*6+4].strip()

            self.properties[square] = MonopolyProperty(self, name,price,rent,group)

    async def play(self):
        for player in self.players:
            self.monopoly_players.append(MonopolyPlayer(player, self))
        self.choosing_colours = True
        embed = discord.Embed(title="Choose you colours", description="use ```!bm colour <colour>```")
        await self.channel.send(embed=embed)

    async def chose_colour(self, player, colour):
        for other in self.monopoly_players:
            if other.colour == colour:
                await self.channel.send("that colour is taken")
                break
        else:
            player.set_colour(colour)
            embed = discord.Embed(title="Set their colour", colour=colour)
            embed.set_author(name=player.user.name, icon_url=player.user.avatar_url)
            await self.channel.send(embed=embed)

            for player in self.monopoly_players:
                if not player.colour:
                    break
            else:
                self.choosing_colours = False
                # self.deciding_order = True
                # self.rolling = self.monopoly_players.copy()
                # embed = discord.Embed(title="Roll for the turn order", description="click the die")
                # message = await self.channel.send(embed=embed)
                # await message.add_reaction("\N{GAME DIE}")
                # self.reaction_messages.append(message)
                for i, player in enumerate(self.monopoly_players):
                    player.set_place(i)
                await self.new_turn()

    async def new_turn(self):
        self.current_turn = self.monopoly_players[self.turn]
        self.rolling = [self.current_turn]
        embed = discord.Embed(title="Your Turn", colour=self.current_turn.colour)
        embed.set_author(name=self.current_turn.user.name, icon_url=self.current_turn.user.avatar_url)
        self.board.update()
        with open("images/upload.png", "rb") as upload:
            file = discord.File(upload, "board.png")
            embed.set_image(url="attachment://board.png")
            message = await self.channel.send(embed=embed, file=file)
        await message.add_reaction("\N{GAME DIE}")
        self.reaction_messages.append(message)
        self.turn += 1
        self.turn %= len(self.monopoly_players)

    async def reaction_add(self, reaction, user):
        for player in self.monopoly_players:
            if player.user == user:

                if reaction.emoji == "\N{GAME DIE}" and player in self.rolling:
                    await self.roll(player)

    async def reaction_remove(self, user, reaction):
        pass

    async def roll(self, player):
        roll1 = random.randint(1, 6)
        roll2 = random.randint(1, 6)
        await player.rolled(roll1, roll2)

        if self.deciding_order:
            pass
        else:
            player.move(roll1 + roll2)
            if player.square in self.properties:
                await self.properties[player.square].display()
            await self.new_turn()

class MonopolyPlayer:

    def __init__(self, user, game):
        self.user = user
        self.game = game
        self.colour = None
        self.place = None
        self.square = 0

    def set_colour(self, colour):
        self.colour = colour

    def set_place(self, place):
        self.place = place

    def move(self, amount):
        self.square += amount
        self.square %= 40

    async def rolled(self, roll1, roll2):
        tw = 1000
        th = 500
        image = Image.new("RGBA", (tw,th), color=(255,255,255,0))
        face = Image.open("images/dice"+str(roll1)+".png")
        w, h = face.size
        image.paste(face, (0, 0, w, h))
        face = Image.open("images/dice"+str(roll2)+".png")
        w, h = face.size
        image.paste(face, (tw-w, 0, tw, h))
        image = image.resize((400, 200))
        image.save("images/upload.png", "PNG", optimize=True)
        embed = discord.Embed(title=f"Rolled {roll1+roll2}", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        with open("images/upload.png", "rb") as upload:
            file = discord.File(upload, "dice.png")
            embed.set_image(url="attachment://dice.png")
            await self.game.channel.send(embed=embed, file=file)

class MonopolyBoard:

    def __init__(self, game):
        self.game = game

    def pos(self, square, d):
        if square == 0:
            y = 695
            x = 695
        elif square > 0 and square < 5:
            y = 695
            x = 695-65*square
        elif square >= 5 and square < 10:
            y = 695
            x = 367-65*(square-5)
        elif square == 10:
            y = 695
            x = 0
        elif square > 10 and square < 15:
            y = 694-65*(square-10)
            x = 106-d
        elif square >= 15 and square < 20:
            y = 366-65*(square-15)
            x = 106-d
        elif square == 20:
            y = 0
            x = 0
        elif square > 20 and square < 26:
            y = 0
            x = 105+66*(square-21)
        elif square > 25 and square < 30:
            y = 0
            x = 435+65*(square-26)
        elif square == 30:
            y = 0
            x = 695
        elif square > 30 and square < 34:
            y = 105+66*(square-31)
            x = 694
        elif square >= 34 and square < 38:
            y = 301+66*(square-34)
            x = 694
        elif square >= 38 and square < 40:
            y = 564+65*(square-38)
            x = 694
        elif square == 40:
            y = 695
            x = 31
        return x,y

    def update(self):
        d = 20
        board = Image.open("images/board.jpg").convert("RGBA")
        draw = ImageDraw.Draw(board)
        for player in self.game.monopoly_players:
            square = player.square
            i = player.place
            colour = player.colour.to_rgb()
            x,y = self.pos(square, d)
            xc = i%2
            yc = i//2
            if square in [0,20,30]:
                xpad = xc*40+20
                ypad = yc*30+15
            elif square in [1,3,6,8,9]:
                xpad = xc*30+7
                ypad = yc*25+30
            elif square in [2,4,5,7]:
                xpad = xc*30+7
                ypad = yc*35+7
            elif square == 10:
              if i < 4:
                xpad = 5
                ypad = i*25+5
              else:
                xpad = 10+35*(i-3)
                ypad = 80
            elif square in [11,13,14,16,18,19]:
                xpad = -(yc*25+30)
                ypad = xc*30+7
            elif square in [12,15,17]:
                xpad = -(yc*36+8)
                ypad = xc*30+7
            elif square in [21,23,24,26,27,29]:
                xpad = xc*30+7
                ypad = yc*25+4
            elif square in [22,25,28]:
                xpad = xc*30+7
                ypad = yc*35+7
            elif square in [31,32,34,37,39]:
                xpad = yc*25+30
                ypad = xc*30+7
            elif square in [33,35,36,38]:
                xpad = yc*35+7
                ypad = xc*30+8
            elif square == 40:
                xpad = xc*35+10
                ypad = yc*22+3
            x0 = x+xpad
            y0 = y+ypad
            x1 = x0+d
            y1 = y0+d
            draw.ellipse([x0,y0,x1,y1], fill=colour, outline="black", width=1)
        for p in self.game.properties:
            prop = self.game.properties[p]
            square = p
            x,y = self.pos(p, 18)
            if prop.owner != None:
                colour = prop.owner.colour.to_rgb()
                cw = 65
                ch = 8
                if square in [1,3,5,6,8,9]:
                    xpad = 0
                    ypad = -1
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+cw
                    y1 = y0-ch
                if square in [11,12,13,14,15,16,18,19]:
                    xpad = 19
                    ypad = 0
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+ch
                    y1 = y0+cw
                if square in [21,23,24,25,26,27,28,29]:
                    xpad = 0
                    ypad = 106
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+cw
                    y1 = y0+ch
                if square in [31,32,34,35,37,39]:
                    xpad = -1
                    ypad = 0
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0-ch
                    y1 = y0+cw
                draw.rectangle([x0,y0,x1,y1], fill=colour)
            dd = [13,18]
            colour = "green"
            for i in range(prop.houses):
                if square in [1,3,6,8,9]:
                    xpad = i*15+3
                    ypad = 2
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+dd[0]
                    y1 = y0+dd[1]
                elif square in [11,13,14,16,18,19]:
                    xpad = -3
                    ypad = i*15+3
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+dd[1]
                    y1 = y0+dd[0]
                elif square in [21,23,24,26,27,29]:
                    xpad = i*15+3
                    ypad = 83
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+dd[0]
                    y1 = y0+dd[1]
                elif square in [31,32,34,37,39]:
                    xpad = 4
                    ypad = i*15+3
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+dd[1]
                    y1 = y0+dd[0]
                draw.rectangle([x0,y0,x1,y1], fill=colour, outline="black", width=1)
            if prop.hotel:
                dd = [34,18]
                colour = "red"
                if square in [1,3,6,8,9]:
                    xpad = 15
                    ypad = 2
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+dd[0]
                    y1 = y0+dd[1]
                elif square in [11,13,14,16,18,19]:
                    xpad = -3
                    ypad = 15
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+dd[1]
                    y1 = y0+dd[0]
                elif square in [21,23,24,26,27,29]:
                    xpad = 17
                    ypad = 84
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+dd[0]
                    y1 = y0+dd[1]
                elif square in [31,32,34,37,39]:
                    xpad = 3
                    ypad = 16
                    x0 = x+xpad
                    y0 = y+ypad
                    x1 = x0+dd[1]
                    y1 = y0+dd[0]
                draw.rectangle([x0,y0,x1,y1], fill=colour, outline="black", width=1)
        board.save("images/upload.png", "PNG", optimize=True)
        # board1 = board.crop((0,0,800,400))
        # board2 = board.crop((0,400,800,800))
        # board1.resize((1200,600))
        # board2.resize((1200,600))
        # board1.save("images/upload1.png", "PNG", optimize=True)
        # board2.save("images/upload2.png", "PNG", optimize=True)
        # with open("images/upload1.png", "rb") as upload1, open("images/upload2.png", "rb") as upload2:
        #     bfiles = [discord.File(upload1, "board1.png"), discord.File(upload2, "board2.png")]
        #     await self.channel.send(files=bfiles)
        
##        board.save("images/upload.png", "PNG", optimize=True)
##        with open("images/upload.png", "rb") as upload:
##            await self.channel.send(file=discord.File(upload, "board.png"))

class MonopolyProperty:

    def __init__(self, game, name, price, rent, group):
        self.game = game
        self.name = name
        self.price = price
        self.rent = rent
        self.group = group
        try:
            self.house_price = {"brown":50,"light blue":50,"pink":100,"orange":100,"red":150,"yellow":150,"green":200,"dark blue":200}[self.group]
        except KeyError:
            self.house_price = None
        self.mortgaged = False
        self.owner = None
        self.houses = 0
        self.hotel = False

    async def display(self):
        embed = discord.Embed(title=self.name)
        if self.group == "station":
            embed.colour = discord.Colour.default()
            embed.description = ("""
Title Deed: %s\n
Rent: M25
If 2 stations are owned: M50
If 3 stations are owned: M100
If 4 stations are owned: M200\n
mortgage value: M100"""%(self.name))

        elif self.group == "utility":
            embed.colour = discord.Colour.from_rgb(255, 255, 255)
            embed.description = ("""
Title Deed: %s\n
If one "Utility" is owned, rent
is 4 times amount shown
on dice.\n
If both "Utilities" are owned,
rent is 10 times amount
shown on dice.\n
mortgage value: M75"""%(self.name))
        else:
            embed.colour = discord.Colour.from_rgb(*ImageColor.getrgb(self.group.replace(" ", "")))
            embed.description = f"""
Title Deed: {self.name}\n
Rent - site only: M{self.rent[0]}
with 1 house: M{self.rent[1]}
with 2 houses: M{self.rent[2]}
with 3 houses: M{self.rent[3]}
with 4 houses: M{self.rent[4]}
with a hotel: M{self.rent[5]}
cost of houses: M{self.house_price}
hotel: M{self.house_price} plus 4 houses\n
mortgage value: M{self.price/2}"""
        if self.owner:
            embed.set_author(name=self.owner.user.name, icon_url=self.owner.user.avatar_url)
        else:
            embed.set_author(name="No Owner")
        await self.game.channel.send(embed=embed)

class Monopoly(Cog):

    def __init__(self, bot):
        self.bot = bot

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
        for game in games:
            if type(game) == MonopolyGame:
                for player in game.monopoly_players:
                    if player.user == ctx.author:
                        await game.chose_colour(player, colour)