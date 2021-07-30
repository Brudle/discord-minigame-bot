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

class BattleshipsPlayer:

    def __init__(self, user, game, colour=None):
        self.user = user
        self.game = game
        self.colour = colour
        self.own_board = BattleshipsBoard()
        self.target_board = BattleshipsBoard()
        self.ships = []
        self.placing_ship = ()
        self.choosing_row = None
        self.row_choice = None
        self.choosing_column = None
        self.column_choice = None
        self.choosing_direction = None
        self.direction_choice = None

    def set_colour(self, colour):
        self.colour = colour

    async def place_next_ship(self):
        self.placing_ship = self.ships_to_place.popleft()
        await self.choose_row(0)

    async def choose_row(self, message=None):
        embed = discord.Embed(title=f"Place Your {self.placing_ship[0]}")
        embed.add_field(name="Choose the Row", value=str(self.own_board))
        if message:
            await message.delete()
        message = await self.user.send(embed=embed)
        for c in range(65, 75):
            if self.own_board.valid_row_choice(chr(c), self.placing_ship[1]):
                await message.add_reaction(emojis[chr(c)])
        self.choosing_row = message
        self.game.reaction_messages.append(message)

    async def chose_row(self, reaction):
        for c in range(65, 75):
            if emojis[chr(c)] == reaction.emoji and self.own_board.valid_row_choice(chr(c), self.placing_ship[1]):
                self.row_choice = chr(c)
                self.own_board.select_row(chr(c))
                self.choosing_row = None
                self.game.reaction_messages.remove(reaction.message)
                await self.choose_column(reaction.message)
                break

    async def choose_column(self, message):
        embed = discord.Embed(title=f"Place Your {self.placing_ship[0]}")
        embed.add_field(name="Choose the Column", value=str(self.own_board))
        await message.delete()
        message = await self.user.send(embed=embed)
        await message.add_reaction(emojis["back"])
        for i in range(1, 11):
            if self.own_board.valid_column_choice(self.row_choice, i, self.placing_ship[1]):
                await message.add_reaction(emojis[i])
        self.choosing_column = message
        self.game.reaction_messages.append(message)

    async def chose_column(self, reaction):
        if reaction.emoji == emojis["back"]:
            self.own_board.deselect_row(self.row_choice)
            self.row_choice = None
            self.choosing_column = None
            self.game.reaction_messages.remove(reaction.message)
            await self.choose_row(reaction.message)
        for i in range(1, 11):
            if emojis[i] == reaction.emoji and self.own_board.valid_column_choice(self.row_choice, i, self.placing_ship[1]):
                self.column_choice = i
                self.own_board.select_column(self.row_choice, i)
                self.choosing_column = None
                self.game.reaction_messages.remove(reaction.message)
                await self.choose_direction(reaction.message)
                break

    async def choose_direction(self, message):
        embed = discord.Embed(title=f"Place Your {self.placing_ship[0]}")
        embed.add_field(name="Choose the Orientation", value=str(self.own_board))
        await message.delete()
        message = await self.user.send(embed=embed)
        await message.add_reaction(emojis["back"])
        for direction in BattleshipsBoard.directions:
            if self.own_board.valid_direction_choice(self.row_choice, self.column_choice, direction, self.placing_ship[1]):
                await message.add_reaction(emojis[direction])
        self.choosing_direction = message
        self.game.reaction_messages.append(message)

    async def chose_direction(self, reaction):
        if reaction.emoji == emojis["back"]:
            self.own_board.select_row(self.row_choice)
            self.column_choice = None
            self.choosing_direction = None
            self.game.reaction_messages.remove(reaction.message)
            await self.choose_column(reaction.message)
        for direction in BattleshipsBoard.directions:
            if emojis[direction] == reaction.emoji and self.own_board.valid_direction_choice(self.row_choice, self.column_choice, direction, self.placing_ship[1]):
                self.direction_choice = direction
                self.own_board.select_direction(self.row_choice, self.column_choice, direction, self.placing_ship[1])
                self.choosing_direction = None
                self.game.reaction_messages.remove(reaction.message)
                await self.confirm_placement(reaction.message)
                break

    async def confirm_placement(self, message):
        embed = discord.Embed(title=f"Place Your {self.placing_ship[0]}")
        embed.add_field(name="Confirm the Placement", value=str(self.own_board))
        await message.delete()
        message = await self.user.send(embed=embed)
        await message.add_reaction(emojis["tick"])
        await message.add_reaction(emojis["cross"])
        self.confirming_placement = message
        self.game.reaction_messages.append(message)

    async def confirmed_placement(self, reaction):
        if reaction.emoji == emojis["cross"]:
            self.own_board.deselect_direction(self.row_choice, self.column_choice, self.direction_choice, self.placing_ship[1])
            self.direction_choice = None
            self.confirming_placement = None
            self.game.reaction_messages.remove(reaction.message)
            await self.choose_direction(reaction.message)
        elif reaction.emoji == emojis["tick"]:
            self.own_board.add_ship(self.row_choice, self.column_choice, self.direction_choice, self.placing_ship[1])
            self.row_choice = None
            self.column_choice = None
            self.direction_choice = None
            self.confirming_placement = None
            self.game.reaction_messages.remove(reaction.message)
            if self.ships_to_place:
                await self.place_next_ship()
            else:
                embed = discord.Embed(title="", description="finished their board setup", colour=self.colour)
                embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                await self.game.channel.send(embed=embed)

class BattleshipsBoard:
    directions = ["LA", "UA", "RA", "DA"]
    directionCoords = {
        "UA": (0, -1),
        "DA": (0, 1),
        "LA": (-1, 0),
        "RA": (1, 0)
        }

    def __init__(self):
        self.board = {chr(c): ["BE" for i in range(10)] for c in range(65, 75)}
        self.ships = []

    def __str__(self):
        return (f"{emojis['BK']}") + ("".join(f"{emojis[i]}" for i in range(1, 11))) + "\n" +\
        ("\n".join(f"{emojis[chr(c)]}" + ("".join(f"{emojis[self.board[chr(c)][i]]}" for i in range(10))) for c in range(65, 75)))

    def valid_row_choice(self, row, size=None):
        if size:
            for i in range(1, 11):
                if self.valid_column_choice(row, i, size):
                    return True
            return False
        for i in range(10):
            if self.board[row][i] == "BE":
                return True
        return False

    def valid_column_choice(self, row, column, size=None):
        if size:
            for direction in BattleshipsBoard.directions:
                if self.valid_direction_choice(row, column, direction, size):
                    return True
            return False
        return self.board[row][column-1] == "BE"

    def valid_direction_choice(self, row, column, direction, size):
        for i in range(size):
            x = column+i*BattleshipsBoard.directionCoords[direction][0]
            y = chr(ord(row)+i*BattleshipsBoard.directionCoords[direction][1])
            if y in self.board and x >= 1 and x <= 10:
                for ship in self.ships:
                    if (y, x) in ship:
                        return False
            else:
                return False
        return True

    def select_row(self, row):
        for i in range(10):
            if self.board[row][i] == "BE":
                self.board[row][i] = "P"

    def deselect_row(self, row):
        for i in range(10):
            if self.board[row][i] == "P":
                self.board[row][i] = "BE"

    def select_column(self, row, column):
        for i in range(10):
            if i != (column-1) and self.board[row][i] == "P":
                self.board[row][i] = "BE"

    def select_direction(self, row, column, direction, size):
        for i in range(size):
            x = column+i*BattleshipsBoard.directionCoords[direction][0]
            y = chr(ord(row)+i*BattleshipsBoard.directionCoords[direction][1])
            self.board[y][x-1] = "BK"

    def deselect_direction(self, row, column, direction, size):
        self.board[row][column-1] = "P"
        for i in range(1, size):
            x = column+i*BattleshipsBoard.directionCoords[direction][0]
            y = chr(ord(row)+i*BattleshipsBoard.directionCoords[direction][1])
            self.board[y][x-1] = "BE"

    def add_ship(self, row, column, direction, size):
        ship = []
        for i in range(size):
            x = column+i*BattleshipsBoard.directionCoords[direction][0]
            y = chr(ord(row)+i*BattleshipsBoard.directionCoords[direction][1])
            ship.append((y, x))
        self.ships.append(ship)

class Battleships(Game):

    def __init__(self, *args):
        super().__init__(*args, maxplayers=2)
        self.battleships_players = []

    async def play(self):
        self.turn = random.randint(0, 1)
        for player in self.players:
            self.battleships_players.append(BattleshipsPlayer(player, self))
        self.battleships_players[0].set_colour(discord.Colour.blue())
        self.battleships_players[1].set_colour(discord.Colour.red())
        for player in self.battleships_players:
            player.ships_to_place = collections.deque([("Battleship", 5), ("Cruiser", 3)])
            await player.place_next_ship()

    async def reaction_add(self, reaction, user):
        for player in self.battleships_players:
            if player.user == user:

                if player.choosing_row == reaction.message:
                    await player.chose_row(reaction)

                elif player.choosing_column == reaction.message:
                    await player.chose_column(reaction)

                elif player.choosing_direction == reaction.message:
                    await player.chose_direction(reaction)

                elif player.confirming_placement == reaction.message:
                    await player.confirmed_placement(reaction)

    async def reaction_remove(self, reaction, user):
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
