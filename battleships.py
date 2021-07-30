import asyncio
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

    def __init__(self, user, game):
        self.user = user
        self.game = game
        self.own_board = BattleshipsBoard()
        self.target_board = BattleshipsBoard()
        self.boards = (self.own_board, self.target_board)
        self.ships = {}
        self.placing_ship = ()
        self.choosing_row = None
        self.row_choice = None
        self.choosing_column = None
        self.column_choice = None
        self.choosing_direction = None
        self.direction_choice = None
        self.setup_board = False
        self.eliminated = False

    def set_colour(self, colour):
        self.colour = colour

    def set_opponent(self, opponent):
        self.opponent = opponent

    async def place_next_ship(self):
        self.placing_ship = self.ships_to_place.popleft()
        await self.choose_row()

    async def choose_row(self, message=None):
        if message:
            await message.delete()
        if not self.setup_board:
            embed = discord.Embed(title=f"Place Your {self.placing_ship[0].capitalize()}")
            embed.add_field(name="Choose the Row", value=str(self.own_board))
            message = await self.user.send(embed=embed)
        else:
            embed = discord.Embed(title=f"{self.user.name}'s Turn to Strike", colour=self.colour)
            embed.set_author(name="", url=self.user.avatar_url)
            embed.add_field(name="Choose the Row", value=str(self.target_board))
            message = await self.game.channel.send(embed=embed)
        for c in range(65, 75):
            if self.boards[self.setup_board].valid_row_choice(chr(c), self.placing_ship[1], (self.ships, None)[self.setup_board]):
                await message.add_reaction(emojis[chr(c)])
        self.choosing_row = message
        self.game.reaction_messages.append(message)

    async def chose_row(self, reaction):
        for c in range(65, 75):
            if emojis[chr(c)] == reaction.emoji and self.boards[self.setup_board].valid_row_choice(chr(c), self.placing_ship[1], (self.ships, None)[self.setup_board]):
                self.row_choice = chr(c)
                self.boards[self.setup_board].select_row(chr(c))
                self.choosing_row = None
                self.game.reaction_messages.remove(reaction.message)
                await self.choose_column(reaction.message)
                break

    async def choose_column(self, message):
        await message.delete()
        if not self.setup_board:
            embed = discord.Embed(title=f"Place Your {self.placing_ship[0].capitalize()}")
            embed.add_field(name="Choose the Column", value=str(self.own_board))
            message = await self.user.send(embed=embed)
        else:
            embed = discord.Embed(title=f"{self.user.name}'s Turn to Strike", colour=self.colour)
            embed.set_author(name="", url=self.user.avatar_url)
            embed.add_field(name="Choose the Column", value=str(self.target_board))
            message = await self.game.channel.send(embed=embed)
        await message.add_reaction(emojis["back"])
        for i in range(1, 11):
            if self.boards[self.setup_board].valid_column_choice(self.row_choice, i, self.placing_ship[1], (self.ships, None)[self.setup_board]):
                await message.add_reaction(emojis[i])
        self.choosing_column = message
        self.game.reaction_messages.append(message)

    async def chose_column(self, reaction):
        if reaction.emoji == emojis["back"]:
            self.boards[self.setup_board].deselect_row(self.row_choice)
            self.row_choice = None
            self.choosing_column = None
            self.game.reaction_messages.remove(reaction.message)
            await self.choose_row(reaction.message)
        for i in range(1, 11):
            if emojis[i] == reaction.emoji and self.boards[self.setup_board].valid_column_choice(self.row_choice, i, self.placing_ship[1], (self.ships, None)[self.setup_board]):
                self.column_choice = i
                self.boards[self.setup_board].select_column(self.row_choice, i)
                self.choosing_column = None
                self.game.reaction_messages.remove(reaction.message)
                if not self.setup_board:
                    await self.choose_direction(reaction.message)
                else:
                    await self.confirm_placement(reaction.message)
                break

    async def choose_direction(self, message):
        embed = discord.Embed(title=f"Place Your {self.placing_ship[0].capitalize()}")
        embed.add_field(name="Choose the Orientation", value=str(self.own_board))
        await message.delete()
        message = await self.user.send(embed=embed)
        await message.add_reaction(emojis["back"])
        for direction in BattleshipsBoard.directions:
            if self.own_board.valid_direction_choice(self.row_choice, self.column_choice, direction, self.placing_ship[1], self.ships):
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
            if emojis[direction] == reaction.emoji and self.own_board.valid_direction_choice(self.row_choice, self.column_choice, direction, self.placing_ship[1], self.ships):
                self.direction_choice = direction
                self.own_board.select_direction(self.row_choice, self.column_choice, direction, self.placing_ship[1])
                self.choosing_direction = None
                self.game.reaction_messages.remove(reaction.message)
                await self.confirm_placement(reaction.message)
                break

    async def confirm_placement(self, message):
        await message.delete()
        if not self.setup_board:
            embed = discord.Embed(title=f"Place Your {self.placing_ship[0].capitalize()}")
            embed.add_field(name="Confirm the Placement", value=str(self.own_board))
            message = await self.user.send(embed=embed)
        else:
            embed = discord.Embed(title=f"{self.user.name}'s Turn to Strike", colour=self.colour)
            embed.set_author(name="", url=self.user.avatar_url)
            embed.add_field(name="Confirm the Strike", value=str(self.target_board))
            message = await self.game.channel.send(embed=embed)
        await message.add_reaction(emojis["tick"])
        await message.add_reaction(emojis["cross"])
        self.confirming_placement = message
        self.game.reaction_messages.append(message)

    async def confirmed_placement(self, reaction):
        if reaction.emoji == emojis["cross"]:
            self.confirming_placement = None
            self.game.reaction_messages.remove(reaction.message)
            if not self.setup_board:
                self.own_board.deselect_direction(self.row_choice, self.column_choice, self.direction_choice, self.placing_ship[1])
                self.direction_choice = None
                await self.choose_direction(reaction.message)
            else:
                self.target_board.select_row(self.row_choice)
                self.column_choice = None
                await self.choose_column(reaction.message)
        elif reaction.emoji == emojis["tick"]:
            self.confirming_placement = None
            self.game.reaction_messages.remove(reaction.message)
            if not self.setup_board:
                self.add_ship()
                self.row_choice = None
                self.column_choice = None
                self.direction_choice = None
                self.placing_ship = (None, None)
                if self.ships_to_place:
                    await self.place_next_ship()
                else:
                    embed = discord.Embed(title="", description="Finished their board setup", colour=self.colour)
                    embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                    await self.game.channel.send(embed=embed)
                    embed = discord.Embed(title="Setup Complete", description=f"Head back to the game {self.game.channel.mention}")
                    await self.user.send(embed=embed)
                    self.setup_board = True
                    await self.game.setup_finished()
            else:
                await self.strike(self.row_choice, self.column_choice)
                self.row_choice = None
                self.column_choice = None

    def add_ship(self):
        coords = []
        for i in range(self.placing_ship[1]):
            x = self.column_choice+i*BattleshipsBoard.directionCoords[self.direction_choice][0]
            y = chr(ord(self.row_choice)+i*BattleshipsBoard.directionCoords[self.direction_choice][1])
            coords.append((y, x))
        self.ships[self.placing_ship[0]] = coords

    async def strike(self, row, column):
        embed = discord.Embed(title=f"Strike confirmed on {row}{column}", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
        await asyncio.sleep(2)
        for ship in self.opponent.ships:
            if (row, column) in self.opponent.ships[ship]:
                embed = discord.Embed(title="Hit!", colour=self.colour)
                embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                await self.game.channel.send(embed=embed)
                self.opponent.ships[ship].remove((row, column))
                self.target_board.set_square(row, column, "R")
                self.opponent.own_board.set_square(row, column, "R")
                if len(self.opponent.ships[ship]) == 0:
                    embed = discord.Embed(title="Sunk!", description=f"Enemy {ship} sunk", colour=self.colour)
                    embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                    await self.game.channel.send(embed=embed)
                    self.opponent.ships.pop(ship)
                    await self.opponent.turn_update(True, True, ship)
                else:
                    await self.opponent.turn_update(True, False, ship)
                break
        else:
            self.target_board.set_square(row, column, "W")
            self.opponent.own_board.set_square(row, column, "W")
            embed = discord.Embed(title="Miss", colour=self.colour)
            embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
            await self.game.channel.send(embed=embed)
            await self.opponent.turn_update(False, False, None)
        await self.game.tick()

    async def turn_update(self, hit, sunk, ship):
        if hit:
            embed = discord.Embed(title=f"Your {ship} was {('hit', 'sunk')[sunk]}!", description=str(self.own_board))
        else:
            embed = discord.Embed(title=f"The enemy missed!", description=str(self.own_board))
        await self.user.send(embed=embed)


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

    def __str__(self):
        return (f"{emojis['BK']}") + ("".join(f"{emojis[i]}" for i in range(1, 11))) + "\n" +\
        ("\n".join(f"{emojis[chr(c)]}" + ("".join(f"{emojis[self.board[chr(c)][i]]}" for i in range(10))) for c in range(65, 75)))

    def set_square(self, row, column, colour):
        self.board[row][column-1] = colour

    def valid_row_choice(self, row, size=None, ships=None):
        if size:
            for i in range(1, 11):
                if self.valid_column_choice(row, i, size, ships):
                    return True
            return False
        for i in range(10):
            if self.board[row][i] == "BE":
                return True
        return False

    def valid_column_choice(self, row, column, size=None, ships=None):
        if size:
            for direction in BattleshipsBoard.directions:
                if self.valid_direction_choice(row, column, direction, size, ships):
                    return True
            return False
        return self.board[row][column-1] == "P"

    def valid_direction_choice(self, row, column, direction, size, ships):
        for i in range(size):
            x = column+i*BattleshipsBoard.directionCoords[direction][0]
            y = chr(ord(row)+i*BattleshipsBoard.directionCoords[direction][1])
            if y in self.board and x >= 1 and x <= 10:
                for ship in ships:
                    if (y, x) in ships[ship]:
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

class Battleships(Game):

    def __init__(self, *args):
        super().__init__(*args, maxplayers=2)
        self.battleships_players = []
        self.game_over = False
        self.winner = None

    async def play(self):
        for player in self.players:
            self.battleships_players.append(BattleshipsPlayer(player, self))
        self.battleships_players[0].set_colour(discord.Colour.blue())
        self.battleships_players[1].set_colour(discord.Colour.red())
        self.battleships_players[0].set_opponent(self.battleships_players[1])
        self.battleships_players[1].set_opponent(self.battleships_players[0])
        for player in self.battleships_players:
            player.ships_to_place = collections.deque([
                ("carrier", 5),
                ("battleship", 4),
                ("cruiser", 3),
                ("submarine", 3),
                ("destoryer", 2)
            ])
            await player.place_next_ship()

    async def setup_finished(self):
        for player in self.battleships_players:
            if not player.setup_board:
                return False

        self.turn = random.randint(0, 1)
        self.current_turn = self.battleships_players[self.turn]
        self.round = 1
        self.turns_in_round = 0
        await self.tick()

    async def tick(self):
        self.turns_in_round += 1
        if self.turns_in_round == 2:
            for player in self.battleships_players:
                if not player.ships:
                    player.eliminated = True
            if self.battleships_players[0].eliminated and self.battleships_players[1].eliminated:
                self.game_over = True
            elif self.battleships_players[0].eliminated:
                self.winner = self.battleships_players[1]
                self.game_over = True
            elif self.battleships_players[1].eliminated:
                self.winner = self.battleships_players[0]
                self.game_over = True
        if not self.game_over:
            self.turn = not self.turn
            self.current_turn = self.battleships_players[self.turn]
            embed = discord.Embed(title=f"Round {self.round}")
            await self.channel.send(embed=embed)
            await self.current_turn.choose_row()
        else:
            if not self.winner:
                embed = discord.Embed(title="It's a draw!")
            else:
                embed = discord.Embed(title=f"Won the game!", colour=self.winner.colour)
                embed.set_author(name=self.winner.user.name, icon_url=self.winner.user.avatar_url)
            await self.channel.send(embed=embed)

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
