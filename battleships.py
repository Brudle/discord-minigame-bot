import discord
from discord.ext.commands import command, Cog, Greedy
import random
import collections
from game import Game, games

emojis = {
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
"RA": "\N{BLACK RIGHTWARDS ARROW}",
"back": "\N{LEFTWARDS ARROW WITH HOOK}",
"tick": "\N{WHITE HEAVY CHECK MARK}",
"cross": "\N{CROSS MARK}"
}

for i in range(10):
    emojis[i] = f"{i}\N{COMBINING ENCLOSING KEYCAP}"

class Battleships(Game):

    def __init__(self, *args):
        super().__init__(*args, maxplayers=2)
        self.empty_board = {chr(c): ["BE" for i in range(10)] for c in range(65, 75)}
        self.boards = {}
        self.ships_to_place = {}
        self.ships = {}
        self.placing_ship = {}
        self.placing_ship_size = {}
        self.choosing_row = {}
        self.choosing_column = {}
        self.choosing_orientation = {}
        self.chose_orientation = {}
        self.confirming_placement = {}
        self.choosing_row = {}
        self.chose_row = {}
        self.choosing_column = {}
        self.chose_column = {}

    async def play(self):
        self.turn = random.randint(0, 1)
        for player in self.players:
            self.boards[player] = self.empty_board.copy()
            self.ships_to_place[player] = collections.deque([("Battleship", 5), ("Cruiser", 3)])
            self.ships[player] = []
            await self.place_next_ship(player)

    async def place_next_ship(self, player):
        self.placing_ship[player], self.placing_ship_size[player] =\
        self.ships_to_place[player].popleft()
        await self.choose_row(player)

    def print_board(self, board):
        return (f"{emojis['BK']}") + ("".join(f"{emojis[i]}" for i in range(1, 11))) + "\n" +\
        ("\n".join(f"{emojis[chr(c)]}" + ("".join(f"{emojis[board[chr(c)][i]]}" for i in range(10))) for c in range(65, 75)))

    async def reaction_add(self, reaction, user):
        for player in self.players:
            if player == user:

                if self.choosing_row[player] == reaction.message:
                    self.choosing_row[player] = None
                    self.reaction_messages.remove(reaction.message)
                    for c in range(65, 76):
                        if emojis[chr(c)] ==  reaction.emoji:
                            for i in range(10):
                                if self.boards[player][chr(c)][i]  == "BE":
                                    self.boards[player][chr(c)][i] = "P"
                            self.chose_row[player] = chr(c)
                            await self.choose_column(player, reaction.message)
                            break

                elif self.choosing_column[player] == reaction.message:
                    self.choosing_column[player] = None
                    self.reaction_messages.remove(reaction.message)
                    if reaction.emoji == emojis["back"]:
                        for i in range(10):
                            if self.boards[player][self.chose_row[player]][i] == "P":
                                self.boards[player][self.chose_row[player]][i] = "BE"
                        self.chose_row[player] = None
                        await self.choose_row(player, reaction.message)
                        break
                    for i in range(1, 11):
                        if emojis[i] == reaction.emoji and self.boards[player][self.chose_row[player]][i-1] == "P":
                            for j in range(10):
                                if j != (i - 1):
                                    self.boards[player][self.chose_row[player]][j] = "BE"
                            self.chose_column[player] = i
                            await self.choose_orientation(player, reaction.message)
                            break

                elif self.choosing_orientation[player] == reaction.message:
                    self.choosing_orientation[player] = None
                    self.reaction_messages.remove(reaction.message)
                    if reaction.emoji == emojis["back"]:
                        for square in self.boards[player][self.chose_row[player]]:
                            if square == "BE":
                                square = "P"
                        await self.choose_column(player, reaction.message)
                        break
                    for direction in ["UA", "DA", "LA", "RA"]:
                        if emojis[direction] == reaction.emoji and self.valid_placement(self.boards[player], self.chose_row[player],
                        self.chose_column[player], direction, self.placing_ship_size[player]):
                            self.chose_orientation[player] = direction
                            await self.confirm_placement(player, reaction.message)
                            break

                elif self.confirming_placement[player] == reaction.message:
                    self.confirming_placement[player] = None
                    self.reaction_messages.remove(reaction.message)
                    if reaction.emoji == emojis["cross"]:
                        self.reject_ship_placement(self.boards[player], self.chose_row[player],
                        self.chose_column[player], self.chose_orientation[player], self.placing_ship_size[player])
                        self.chose_orientation[player] = None
                        await self.choose_orientation(player, reaction.message)
                    elif reaction.emoji == emojis["tick"]:
                        self.confirm_ship_placement(player, self.chose_row[player], self.chose_column[player],
                        self.chose_orientation[player], self.placing_ship_size[player])
                        if self.ships_to_place[player]:
                            await self.place_next_ship(player)
                        else:
                            embed = discord.Embed(title=f"{player.name} has setup their board", image=player.avatar_url,
                            colour=player.colour)
                            embed.set_image(player.avatar_url)
                            await self.channel.send(embed=embed)

    async def reaction_remove(self, reaction, user):
        pass

    async def choose_row(self, player, message=None):
        embed = discord.Embed(title=f"Place Your {self.placing_ship[player]}")
        embed.add_field(name="Choose the Row", value=self.print_board(self.boards[player]))
        if message:
            await message.delete()
        message = await player.send(embed=embed)
        for c in range(65, 75):
            await message.add_reaction(emojis[chr(c)])
        self.choosing_row[player] = message
        self.reaction_messages.append(message)

    async def choose_column(self, player, message):
        embed = discord.Embed(title=f"Place Your {self.placing_ship[player]}")
        embed.add_field(name="Choose the Column", value=self.print_board(self.boards[player]))
        await message.delete()
        message = await player.send(embed=embed)
        await message.add_reaction(emojis["back"])
        for i in range(1, 11):
            if self.boards[player][self.chose_row[player]][i-1] == "P":
                await message.add_reaction(emojis[i])
        self.choosing_column[player] = message
        self.reaction_messages.append(message)

    async def choose_orientation(self, player, message):
        embed = discord.Embed(title=f"Place Your {self.placing_ship[player]}")
        embed.add_field(name="Choose the Orientation", value=self.print_board(self.boards[player]))
        await message.delete()
        message = await player.send(embed=embed)
        await message.add_reaction(emojis["back"])
        for direction in ["UA", "DA", "LA", "RA"]:
            if self.valid_placement(self.boards[player], self.chose_row[player],
            self.chose_column[player], direction, self.placing_ship_size[player]):
                await message.add_reaction(emojis[direction])
        self.choosing_orientation[player] = message
        self.reaction_messages.append(message)

    async def confirm_placement(self, player, message):
        self.place_ship(self.boards[player], self.chose_row[player], self.chose_column[player],
        self.chose_orientation[player], self.placing_ship_size[player])
        embed = discord.Embed(title=f"Place Your {self.placing_ship[player]}")
        embed.add_field(name="Confirm the Placement", value=self.print_board(self.boards[player]))
        await message.delete()
        message = await player.send(embed=embed)
        await message.add_reaction(emojis["tick"])
        await message.add_reaction(emojis["cross"])
        self.confirming_placement[player] = message
        self.reaction_messages.append(message)

    def valid_placement(self, board, row, column, direction, size):
        directions = {
        "UA": (0, -1),
        "DA": (0, 1),
        "LA": (-1, 0),
        "RA": (1, 0)
        }
        for i in range(1, size):
            x = column+i*directions[direction][0]
            y = chr(ord(row)+i*directions[direction][1])
            if y in board and x >= 1 and x <= 10 and board[y][x-1] == "BE":
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
            board[y][x-1] = "BK"

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
            ship.append((y, x-1))
        self.ships[player].append(ship)

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
            board[y][x-1] = "BE"
        board[row][column-1] = "P"

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
