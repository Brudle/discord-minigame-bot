import discord
from PIL import Image, ImageDraw, ImageColor

class MonopolyBoard:

    def __init__(self, game):
        self.game = game

    def pos(self, square, d):
        if square == "jail":
            y = 695
            x = 31
        elif square == 0:
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
        return x, y

    def update(self):
        d = 20
        board = Image.open("images/board.jpg").convert("RGBA")
        draw = ImageDraw.Draw(board)
        for player in self.game.players:
            square = player.square
            i = player.place
            colour = player.colour.to_rgb()
            x,y = self.pos(square, d)
            xc = i%2
            yc = i//2
            if square == "jail":
                xpad = xc*35+10
                ypad = yc*22+3
            elif square in [0,20,30]:
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
        
    #    board.save("images/upload.png", "PNG", optimize=True)
    #    with open("images/upload.png", "rb") as upload:
    #        await self.channel.send(file=discord.File(upload, "board.png"))

    async def display(self, embed):
        with open("images/upload.png", "rb") as upload:
            file = discord.File(upload, "board.png")
            embed.set_image(url="attachment://board.png")
            return embed, file

class MonopolyProperty:
    groups = ["brown", "light blue", "pink", "orange", "red", "yellow", "green", "dark blue"]

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

    def set_owner(self, player):
        self.owner = player
        if self.group == "station":
            self.owner.stations += 1
        elif self.group == "utility":
            self.owner.utilities += 1

    def can_buy_house(self):
        if not self.hotel and self.houses < 4 and self.owner.owns_group(self.group):
            for prop in self.game.property_group(self.group):
                if prop.houses < self.houses:
                    return False
            return True
        return False

    def can_sell_house(self):
        if self.houses > 0 and self.owner.owns_group(self.group):
            for prop in self.game.property_group(self.group):
                if prop.hotel or prop.houses > self.houses:
                    return False
            return True
        return False

    def can_buy_hotel(self):
        if self.houses == 4 and self.owner.owns_group(self.group):
            for prop in self.game.property_group(self.group):
               if not (prop.houses == 4 or prop.hotel):
                   return False
            return True
        return False

    def can_sell_hotel(self):
        return self.hotel

    def get_rent(self, roll, double_rent=False):
        if self.group == "station":
            if not double_rent:
                return 25 * self.owner.stations
            else:
                return 50 * self.owner.stations
        elif self.group == "utility":
            if not double_rent:
                return (4, 10)[self.owner.utilities-1] * roll
            else:
                return 10 * roll
        else:
            if self.hotel:
                return self.rent[5]
            else:
                if self.houses == 0 and self.owner.owns_group(self.group):
                    return self.rent[0] * 2
                else:
                    return self.rent[self.houses]

    async def mortgage(self):
        self.mortgaged = True
        await self.display()
        await self.owner.deposit(self.price//2)

    async def unmortgage(self):
        self.mortgaged = False
        await self.display()

    async def display(self):
        if self.mortgaged:
            embed = discord.Embed(title="MORTGAGED", colour=discord.Colour.red())
            embed.description = (f"""```
 
 
{'':-^30}
{self.name.upper():^30}
{f"MORTGAGED FOR M{self.price//2}":^30}
{'':-^30}

{"Card must be turned":^30}
{"this side up if":^30}
{"property is mortgaged.":^30}

            ```""")
        else:
            embed = discord.Embed(title=f"TITLE DEED\n{self.name.upper()}")
            if self.group == "station":
                embed.colour = discord.Colour.default()
                embed.description = ("""
Rent: M25
If 2 stations are owned: M50
If 3 stations are owned: M100
If 4 stations are owned: M200\n
mortgage value: M100""")

            elif self.group == "utility":
                embed.colour = discord.Colour.from_rgb(255, 255, 255)
                embed.description = ("""
If one "Utility" is owned, rent
is 4 times amount shown
on dice.\n
If both "Utilities" are owned,
rent is 10 times amount
shown on dice.\n
mortgage value: M75""")
            else:
                embed.colour = discord.Colour.from_rgb(*ImageColor.getrgb(self.group.replace(" ", "")))
                embed.description = f"""```
{f"RENT M{self.rent[0]}":^34}
{f"With 1 House{'M':>16}{self.rent[1]:>4}":^34} 
{f"With 2 Houses{self.rent[2]:>19}":^34}
{f"With 3 Houses{self.rent[3]:>19}":^34}
{f"With 4 Houses{self.rent[4]:>19}":^34}
{f"With HOTEL M{self.rent[5]}":^34}\n
{f"Mortgage Value M{self.price}":^34}
{f"Houses cost M{self.house_price} each":^34}
{f"Hotels, M{self.house_price} plus 4 houses":^34}\n
{f"{'If a player owns ALL the Lots':<30}":^34}
{f"{'of any Colour-Group, the rent':<30}":^34}
{f"{'is Doubled on Unimproved Lots':<30}":^34}
{f"{'in that group.':<30}":^34}```"""
        if self.owner:
            embed.set_author(name=self.owner.user.name, icon_url=self.owner.user.avatar_url)
        else:
            embed.set_author(name="No Owner")
        await self.game.channel.send(embed=embed)