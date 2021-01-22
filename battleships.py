import discord
import random
from game import Game

emojis = {
1: "\N{DIGIT ONE}",
2: "\N{DIGIT TWO}",
3: "\N{DIGIT THREE}",
4: "\N{DIGIT FOUR}",
5: "\N{DIGIT FIVE}",
6: "\N{DIGIT SIX}",
7: "\N{DIGIT SEVEN}",
8: "\N{DIGIT EIGHT}",
9: "\N{DIGIT NINE}",
10: "\N{DIGIT TEN}",
"A": "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
"B": "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
"C": "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
"D": "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
"E": "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
"F": "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
"G": "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
"H": "\N{REGIONAL INDICATOR SYMBOL LETTER H}",
"I": "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
"J": "\N{REGIONAL INDICATOR SYMBOL LETTER J}",
"B": "\N{BLACK LARGE SQUARE}",
"E": "\N{LARGE BLUE SQUARE}",
"M": "\N{WHITE LARGE SQUARE}"
"H": "\N{LARGE ORANGE SQUARE}"
"S": "\N{LARGE RED SQUARE}"
}

class Battleships(Game):

    def __init__(self, *args):
        super().__init__(*args, maxplayers=2)
        self.empty_board = [["E" for i in range(10)] for j in range(10)]

    async def play(self):
        self.turn = random.randint(0, 1)
        await self.setup_board(self.players[0])
        await self.setup_board(self.players[1])

    async def setup_board(self, player):
        player.ship_board = empty_board.copy()
        ships = {"Battleship": 5, "Cruiser": 3}
        embed = discord.Embed(title="Place Your Ships")
        message = player.send(embed=embed)
        for ship, size in ships.items():
            embed = discord.Embed(title="Place Your {}".format(ship))
            await self.choose_square(player, player, embed)

    def print_board(self, board):
        pass

    async def choose_square(self, player, message):
        pass

    async def choose_orientation(self, player, message):
        pass

    async def confirm_choice(self, player, message):
        pass
