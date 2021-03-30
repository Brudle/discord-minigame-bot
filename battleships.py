import discord
from discord.ext.commands import command, Cog, Greedy
import random
from game import Game, games

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
10: "\N{KEYCAP TEN}",
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
"BK": "\N{BLACK LARGE SQUARE}",
"BE": "\N{LARGE BLUE SQUARE}",
"W": "\N{WHITE LARGE SQUARE}",
"O": "\N{LARGE ORANGE SQUARE}",
"R": "\N{LARGE RED SQUARE}",
"P": "\N{LARGE PURPLE SQUARE}",
"UA": "\N{UPWARDS BLACK ARROW}",
"DA": "\N{DOWNWARDS BLACK ARROW}",
"LA": "\N{LEFTWARDS BLACK ARROW}",
"RA": "\N{UPWARDS BLACK ARROW}",
"back": "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
"tick": "\N{WHITE HEAVY CHECK MARK}",
"cross": "\N{CROSS MARK}"
}

class Battleships(Game):

    def __init__(self, *args):
        super().__init__(*args, maxplayers=2)
        self.empty_board = {chr(c): ["BE" for i in range(10)] for c in range(65, 76)}
        self.boards = {}
        self.ships_to_place = {}
        self.ships = {}
        self.placing_ship = {}
        self.placing_ship_size = {}
        self.choosing_row = {}
        self.choosing_column = {}
        self.choosing_orientation = {}
        self.confirming_placement = {}
        self.chose_row = {}
        self.chose_column = {}

    async def play(self):
        self.turn = random.randint(0, 1)
        for player in self.players:
            self.boards[player] = self.empty_board.copy()
            self.ships_to_place[player] = [("Battleship", 5), ("Cruiser", 3)]
            self.ships[player] = []
            await self.place_next_ship(player)

    async def place_next_ship(self, player):
        self.placing_ship[player], self.placing_ship_size[player] =\
        self.ships_to_place[player].popleft()
        embed = discord.Embed(title="Place Your {ship}")
        message = await player.send(embed=embed)
        await self.choose_row(player, player, message, embed)

    def print_board(self, board):
        return (f"{emojis['BK']}") + (f"{emojis[i]}" for i in range(10)) + "\n" +\
        ((f"{emojis[chr(c)]}" + f"{emojis[board[c][i]]}" + "\n") for c in range(65, 76) for i in range(10))

    async def add_reaction(self, reaction, user):
        for player in self.players:
            if player == user:
                if self.choosing_row[player] == reaction.message:
                    self.choosing_row[player] = None
                    for c in range(65, 76):
                        if emojis[chr[c]] ==  reaction.emoji:
                            self.boards[player][chr(c)] = ["P" for i in range(10)]
                            self.chose_row[player] = chr(c)
                            await self.choose_column(player, player, reaction.message)
                            break
                elif self.choosing_column[player] == reaction.message:
                    self.choosing_column[player] = None
                    if reaction.emoji == emojis["back"]:
                        for i in range(10):
                            if self.boards[player][player.chose_row][i] != "P":
                                self.board[player][player.chose_row] = "BE"
                        self.chose_row[player] = None
                        await self.choose_row(player, player, message)
                        break
                    for i in range(1, 11):
                        if emojis[i] == reaction.emoji:
                            player.board[player.chose_row] = ["BE" for j in range(10) if i != j]
                            player.chose_column = i
                            await self.choose_orientation(player, player, reaction.message)
                            break
                elif player.choosing_orientation == reaction.message:
                    player.choosing_orientation = None
                    if reaction.emoji == emojis["back"]:
                        for i in range(10):
                            if player.board[player.chose_row][i] == "BE":
                                player.board[player.chose_row][i] == "P"
                        break
                    for direction in ["UA", "DA", "LA", "RA"]:
                        if emojis[direcion] == reaction.emoji:
                            player.chose_direction = direction
                            await self.confirm_placement(player, reaction.message)
                elif player.confirming_placement == reaction_message:
                    player.confirming_placement = None
                    if reaction.emoji == emojis["cross"]:
                        self.reject_ship_placement(player.board, player.chose_row,
                        player.chose_column, player.chose_direction, player.placing_ship_size)
                        player.chose_direction = None
                        await self.choose_orientation(player, message)
                    elif reaction.emoji == emojis["tick"]:
                        await self.place_next_ship(player)

    async def choose_row(self, player, message):
        player.choosing_row = message
        embed.add_field(value=self.print_board(player.board))
        await message.edit(embed=embed)
        (await message.add_reaction(emojis[chr(c)]) for c in range(65, 76))

    async def choose_column(self, player, message):
        embed = discord.Embed(title="Choose the Column")
        embed.add_field(value=self.print_board(player.board))
        await message.edit(embed=embed)
        await message.add_reaction(emojis["back"])
        (await message.add_reaction(emojis[i] for i in range(1, 11)))
        player.choosing_column = message

    async def choose_orientation(self, player, message):
        embed = discord.Embed(title="Choose the orientation of your {ship}")
        embed.add_field(value=self.print_board(player.board))
        await message.edit(embed=embed)
        await message.add_reaction(emojis["back"])
        for direction in ["UA", "DA", "LA", "RA"]:
            if self.valid_placement(player.board, player.chose_row. player,
            chose_column, direction, player.placing_ship_size):
                await message.add_reaction(emojis[direcion])
        player.choosing_orientation = message

    async def confirm_placement(self, player, message):
        self.place_ship(player.board, player.chose_row, player.chose_column,
        player.chose_direction, player.placing_ship_size)
        embed = discord.Embed(title="Confirm your {player.placing_ship} placement")
        embed.add_field(value=self.print_board(player.board))
        await message.edit(embed=embed)
        await message.add_reaction(emojis["tick"])
        await message.add_rection(emojis["cross"])
        player.confirming_placement = message

    def valid_placement(self, board, row, column, direction, size):
        directions = {
        "UA": (0, -1),
        "DA": (0, 1),
        "LA": (-1, 0),
        "RA": (1, 0)
        }
        for i in range(size):
            x = column+i*directions[direction][0]
            y = chr(ord(row)+i*directions[direction][1])
            if y in board and x >= 1 and x <= 10 and board[y][x] == "BE":
                pass
            else:
                return False
        return True

    def place_ship(self, board, row, column, direction, size):
        directions = {
        "UA": (0, -1),
        "DA": (0, 1),
        "LA": (-1, 0),
        "RA": (1, 0)
        }
        for i in range(size):
            x = column+i*directions[direction][0]
            y = chr(ord(row)+i*directions[direction][1])
            board[y][x] = "BK"

    def confirm_ship_placement(self, player, row, column, direction, size):
        ship = []
        directions = {
        "UA": (0, -1),
        "DA": (0, 1),
        "LA": (-1, 0),
        "RA": (1, 0)
        }
        for i in range(size):
            x = column+i*directions[direction][0]
            y = chr(ord(row)+i*directions[direction][1])
            ship.append((y, x))
        player.ships.append(ship)

    def reject_ship_placement(self, board, row, column, direction, size):
        directions = {
        "UA": (0, -1),
        "DA": (0, 1),
        "LA": (-1, 0),
        "RA": (1, 0)
        }
        for i in range(size):
            x = column+i*directions[direction][0]
            y = chr(ord(row)+i*directions[direction][1])
            board[y][x] = "BE"
        board[y][x] = "P"

    async def confirm_choice(self, player, message):
        pass

class BattleshipsCog(Cog):

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def battleships(self, ctx, users: Greedy[discord.Member]=None):
        game = Battleships(ctx.channel, ctx.author)
        await game.update_lobby()
        games.append(game)
        if users:
            for user in users:
                await game.invite(user)
