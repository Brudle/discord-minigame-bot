import asyncio
from asyncio.coroutines import iscoroutine
import discord
from discord import message
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
        self.unowned_property_react = None
        self.auction_message = None
        self.collecting_message = None
        self.multiple_auctions = False
        self.chest_has_jail_card = True
        self.chance_has_jail_card = True

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
        embed = discord.Embed(title="Your Turn", colour=self.current_turn.colour)
        embed.set_author(name=self.current_turn.user.name, icon_url=self.current_turn.user.avatar_url)
        self.board.update()
        message = await self.board.display(embed)
        if self.current_turn.square == "jail":
            await self.current_turn.jail_update()
        else:
            self.current_turn.rolled_this_turn = False
            self.rolling = [self.current_turn]
            await message.add_reaction("\N{GAME DIE}")
            self.reaction_messages.append(message)

    async def reaction_add(self, reaction, user):
        for player in self.monopoly_players:
            if player.user == user:

                if reaction.emoji == "\N{GAME DIE}" and player in self.rolling and not player.rolled_this_turn:
                    await self.roll(player)

                elif reaction.message == self.unowned_property_react and player == self.current_turn:
                    if reaction.emoji == "\N{MONEY BAG}":
                        await player.purchase_property(self.properties[player.square])
                    elif reaction.emoji == "\N{HAMMER}":
                        await self.auction(self.properties[player.square])

                elif reaction.message == self.auction_message and player in self.auction_participants:
                    if reaction.emoji == "\N{CROSS MARK}":
                        await self.auction_withdraw(player)

                if reaction.message == player.rent_message:
                    if reaction.emoji == "\N{BANKNOTE WITH DOLLAR SIGN}":
                        await player.pay_rent()
                    elif reaction.emoji == "\N{CROSS MARK}":
                        pass

                elif reaction.message == player.confirm_improvement_message:
                    if reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
                        await player.confirmed_improvement(True)
                    elif reaction.emoji == "\N{CROSS MARK}":
                        await player.confirmed_improvement(False)

                elif reaction.message == player.end_turn_message:
                    if reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
                        await player.end_turn()

                elif reaction.message == player.jail_message:
                    if reaction.emoji == "\N{GAME DIE}":
                        await player.jail_choice("roll")
                    elif reaction.emoji == "\N{BANKNOTE WITH DOLLAR SIGN}":
                        await player.jail_choice("pay")
                    elif reaction.emoji == "\N{TICKET}":
                        await player.jail_choice("card")

                elif reaction.message == player.drawing_message:
                    if reaction.emoji == "\N{BLACK QUESTION MARK ORNAMENT}":
                        if player.drawing == "community":
                            await player.draw_community_chest()
                        elif player.drawing == "chance":
                            await player.draw_chance()

                elif reaction.message == self.collecting_message:
                    if reaction.emoji == "\N{BANKNOTE WITH DOLLAR SIGN}":
                        await self.paid_collection(player)
                    elif reaction.emoji == "\N{CROSS MARK}":
                        await self.player_declares_bankruptcy(player)

                elif reaction.message == player.reaction_message:
                    if reaction.emoji in player.reaction_message_actions:
                        await player.reaction_message_actions[reaction.emoji][0]

    async def reaction_remove(self, user, reaction):
        pass

    async def roll(self, player):
        roll1 = random.randint(1, 6)
        roll2 = random.randint(1, 6)
        await player.rolled(roll1, roll2)

        if self.deciding_order:
            pass
        else:
            player.rolled_this_turn = True
            if roll1 == roll2:
                player.double_count += 1
                embed = discord.Embed(title="Rolled Doubles!", colour=player.colour)
                embed.set_author(name=player.user.name, icon_url=player.user.avatar_url)
                await self.channel.send(embed=embed)
            else:
                player.double_count = 0
            if player.double_count == 3:
                embed = discord.Embed(title="Three Doubles in a Row", descritpion="Sent to jail", colour=player.colour)
                embed.set_author(name=player.user.name, icon_url=player.user.avatar_url)
                await self.channel.send(embed=embed)
                player.double_count = 0
                await player.go_to_jail()
            else:
                if player.double_count == 0:
                    self.turn += 1
                    self.turn %= len(self.monopoly_players)
                await player.move(roll1 + roll2)

    def property_group(self, group):
        return filter(lambda p: p.group == group, self.properties.values())

    async def auction_properties(self, props):
        self.multiple_auctions = True
        self.auction_properties_list = props
        self.auction_number = 0
        await self.auction(props[0])

    async def auction(self, prop):
        self.auction_underway = True
        self.auction_participants = self.monopoly_players.copy()
        self.auction_winner = None
        self.auction_bid = 0
        self.auction_property = prop
        await self.update_auction()
        self.reaction_messages.append(self.auction_message)
        await self.auction_message.add_reaction("\N{CROSS MARK}")

    async def auction_withdraw(self, player):
        self.auction_participants.remove(player)
        embed = discord.Embed(title="Withdrew from the Auction", colour=player.colour)
        embed.set_author(name=player.user.name, icon_url=player.user.avatar_url)
        await self.channel.send(embed=embed)
        await self.update_auction()
        await self.auction_check()

    async def bid(self, player, bid):
        if bid <= self.auction_bid:
            embed = discord.Embed(title="Bid Too Low")
        elif bid > player.balance:
            embed = discord.Embed(title="Insufficient Funds")
        else:
            embed = discord.Embed(title="Successful Bid", description=f"Bid {bid}")
            self.auction_bid = bid
            self.auction_winner = player
            await self.update_auction()
        embed.colour = player.colour
        embed.set_author(name=player.user.name, icon_url=player.user.avatar_url)
        await self.channel.send(embed=embed)
        await self.auction_check()

    async def auction_check(self):
        if len(self.auction_participants) == 0 and not self.auction_winner:
            self.auction_underway = False
            embed = discord.Embed(title=f"{self.auction_property.name} Unsold", description="Auction received no bids")
            await self.channel.send(embed=embed)
            self.auction_message = None
            await self.current_turn.confirm_end_turn()
        elif len(self.auction_participants) == 0 or (len(self.auction_participants) == 1 and self.auction_participants[0] == self.auction_winner):
            self.auction_underway = False
            embed = discord.Embed(title="Won the Auction", colour=self.auction_winner.colour)
            embed.set_author(name=self.auction_winner.user.name, icon_url=self.auction_winner.user.avatar_url)
            await self.channel.send(embed=embed)
            self.auction_message = None
            await self.auction_winner.purchase_property(self.auction_property, self.auction_bid)
        if not self.auction_underway and self.multiple_auctions:
            self.auction_number += 1
            if self.auction_number >= len(self.auction_properties_list):
                self.multiple_auctions = False
                if self.current_turn not in self.monopoly_players:
                    self.current_turn.end_turn()
            else:
                self.auction(self.auction_properties_list[self.auction_number])

    async def update_auction(self):
        embed = discord.Embed(title="Auction", description="```!bm bid <amount>```")
        embed.add_field(name="Property", value=self.auction_property.name, inline=False)
        if self.auction_winner:
            embed.add_field(name="Current Bid", value=f"{self.auction_bid} - {self.auction_winner.user.name}", inline=False)
        else:
            embed.add_field(name="Current Bid", value="No bids")
        if self.auction_participants:
            embed.add_field(name="Participants", value="\n".join(map(lambda p: p.user.name, self.auction_participants)), inline=False)
        else:
            embed.add_field(name="Participants", value="No participants", inline=False)
        if self.auction_message:
            await self.auction_message.edit(embed=embed)
        else:
            self.auction_message = await self.channel.send(embed=embed)

    async def collect_from_everyone(self, player, amount):
        self.collecting_player = player
        self.collecting_amount = amount
        self.collecting_total = 0
        self.left_to_collect = list(filter(lambda p: p != player, self.monopoly_players))
        await self.update_collection()

    async def update_collection(self):
        embed = discord.Embed(title="Collect from Everyone", colour=self.collecting_player.colour)
        embed.set_author(name=self.collecting_player.user.name, icon_url=self.collecting_player.user.avatar_url)
        embed.add_field(name="Amount", value=f"M{self.collecting_amount}", inline=False)
        embed.add_field(name="Left", value="\n".join(map(lambda p: p.user.name, self.left_to_collect), inline=False))
        embed.add_field(name="React", value="\N{BANKNOTE WITH DOLLAR SIGN}\n\N{CROSS MARK}")
        embed.add_field(name="Action", value="Pay\nDeclare bankruptcy")
        if not self.collecting_message:
            self.collecting_message = await self.channel.send(embed=embed)
            await self.collecting_message.add_reaction("\N{BANKNOTE WITH DOLLAR SIGN}")
            await self.collecting_message.add_reaction("\N{CROSS MARK}")
            self.reaction_messages.append(self.collecting_message)
        else:
            await self.collecting_message.edit(embed=embed)
            if not self.left_to_collect:
                self.reaction_messages.remove(self.collecting_message)
                self.collecting_message = None
                await self.collecting_player.deposit(self.collecting_total)
                await self.collecting_player.confirm_end_turn()

    async def paid_collection(self, player):
        if player.withdraw(self.collecting_amount):
            self.collecting_total += self.collecting_amount
            self.left_to_collect.remove(player)
            await self.update_collection()

    async def player_declares_bankruptcy(self, player):
        if player.declare_bankruptcy():
            self.left_to_collect.remove(player)
            await self.update_collection()

    async def confirm_bankrupt(self, player):
        self.monopoly_players.remove(player)
        if len(self.monopoly_players) == 1:
            embed = discord.Embed(title="Won the game!", colour=self.monopoly_players[0].colour)
            embed.set_author(name=self.monopoly_players[0].user.name, icon_url=self.monopoly_players[0].user.avatar_url)

class MonopolyPlayer:

    def __init__(self, user, game):
        self.user = user
        self.game = game
        self.colour = None
        self.place = None
        self.square = 0
        self.portfolio = []
        self.double_count = 0
        self.balance = 1500
        self.turns_in_jail = 0
        self.rent = 0
        self.roll = 0
        self.stations = 0
        self.utilities = 0
        self.rent_message = None
        self.confirm_improvement_message = None
        self.rolled_this_turn = False
        self.end_turn_message = None
        self.passed_go = False
        self.chest_jail_card = False
        self.chance_jail_card = False
        self.jail_message = None
        self.drawing = None
        self.drawing_message = None
        self.reaction_message = None
        self.reaction_message_actions = None
        self.double_rent = False

    def set_colour(self, colour):
        self.colour = colour

    def set_place(self, place):
        self.place = place

    def set_square(self, square, collect=False):
        self.square = square

    async def move(self, amount):
        self.square += amount
        if self.square >= 40:
            self.passed_go = True
        self.square %= 40
        await self.evaluate_square()

    async def confirm_end_turn(self):
        if self.double_count:
            await self.game.new_turn()
            return False
        embed = discord.Embed(title="", description="Check to end your turn", colour=self.colour)
        embed.add_field(name="Available Commands", value="""```
!bm buy       <improvement> <group> <property>
!bm view      <property>
!bm portfolio (player)
!bm trade     <player>```""")
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        self.end_turn_message = await self.game.channel.send(embed=embed)
        await self.end_turn_message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        self.game.reaction_messages.append(self.end_turn_message)

    async def end_turn(self):
        self.game.reaction_messages.remove(self.end_turn_message)
        self.end_turn_message = None
        await self.game.new_turn()

    async def evaluate_square(self):
        self.reaction_message = None
        embed = discord.Embed(title="", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        self.game.board.update()
        await self.game.board.display(embed)
        if self.passed_go:
            await self.pass_go()

        if self.square in self.game.properties:
            prop = self.game.properties[self.square]
            await prop.display()
            if not prop.owner:
                embed = discord.Embed(title="Landed on a Property with No Owner", description=prop.name, colour=self.colour)
                embed.add_field(name="Price", value=f"M{prop.price}", inline=False)
                embed.add_field(name="React", value="\N{MONEY BAG}\n\N{HAMMER}")
                embed.add_field(name="Action", value="Purchase the property\nAuction the property")
                embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                message = await self.game.channel.send(embed=embed)
                await message.add_reaction("\N{MONEY BAG}")
                await message.add_reaction("\N{HAMMER}")
                self.game.reaction_messages.append(message)
                self.game.unowned_property_react = message
            elif prop.owner == self:
                await self.confirm_end_turn()
            else:
                self.rent = prop.get_rent(self.roll, self.double_rent)
                embed = discord.Embed(title="Rent Due", description=f"M{self.rent}", colour=self.colour)
                embed.add_field(name="React", value="\N{BANKNOTE WITH DOLLAR SIGN}\n\N{CROSS MARK}")
                embed.add_field(name="Action", value="Pay the rent\nDeclare bankruptcy")
                embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                self.rent_message = await self.game.channel.send(embed=embed)
                await self.rent_message.add_reaction("\N{BANKNOTE WITH DOLLAR SIGN}")
                await self.rent_message.add_reaction("\N{CROSS MARK}")
                self.game.reaction_messages.append(self.rent_message)

        elif self.square == 10:
            embed = discord.Embed(title="Jail", description="Just Visiting", colour=discord.Colour.dark_gray())
            await self.game.channel.send(embed=embed)
            await self.confirm_end_turn()

        elif self.square == 20:
            embed = discord.Embed(title="Free Parking", colour=discord.Colour.from_rgb(255, 255, 255))
            await self.game.channel.send(embed=embed)
            await self.confirm_end_turn()

        elif self.square == 30:
            embed = discord.Embed(title="Go To Jail", colour=discord.Colour.dark_blue())
            await self.game.channel.send(embed=embed)
            await self.go_to_jail()

        elif self.square == 4:
            embed = discord.Embed(title="Income Tax", description="Pay M200")
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(200), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })

        elif self.square in (2, 17, 33):
            embed = discord.Embed(title="Community Chest", description="Draw a card", colour=self.colour)
            embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
            await self.create_reaction_message(embed, **{
                "\N{BLACK QUESTION MARK ORNAMENT}": (self.draw_community_chest(), "Draw a card")
            })

        elif self.square in (7, 22, 36):
            embed = discord.Embed(title="Chance")
            await self.create_reaction_message(embed, **{
                "\N{BLACK QUESTION MARK ORNAMENT}": (self.draw_chance(), "Draw a card")
            })

        else:
            await self.confirm_end_turn()

        self.double_rent = False

    async def pay_rent(self):
        if await self.withdraw(self.rent):
            await self.game.properties[self.square].owner.deposit(self.rent)
            self.rent = 0
            self.game.reaction_messages.remove(self.rent_message)
            self.rent_message = None
            await self.confirm_end_turn()

    async def purchase_property(self, prop, price=None):
        if await self.withdraw(price or prop.price):
            embed = discord.Embed(title="Purchased a Property", description=prop.name, colour=self.colour)
            embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
            await self.game.channel.send(embed=embed)
            self.aquire(prop)
            self.game.unowned_property_react = None
            if not price:
                await self.confirm_end_turn()
        if price and not self.game.multiple_auctions:
            await self.game.current_turn.confirm_end_turn()

    def aquire(self, prop):
        self.portfolio.append(prop)
        prop.set_owner(self)

    def owns_group(self, group):
        for prop in self.game.properties:
            p = self.game.properties[prop]
            if p.group == group and p.owner != self:
                return False
        return True

    async def pass_go(self):
        embed = discord.Embed(title="Passed GO", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        embed = discord.Embed(title="GO", description="Collect M200 salary as you pass", colour=discord.Colour.red())
        await self.game.channel.send(embed=embed)
        await self.deposit(200)
        self.passed_go = False

    async def create_reaction_message(self, embed, **kwargs):
        embed.add_field(name="React", value="\n".join(kwargs.keys()))
        embed.add_field(name="Action", value="\n".join(map(lambda r: r[1], kwargs.values())))
        message = await self.game.channel.send(embed=embed)
        for reaction in kwargs:
            await message.add_reaction(reaction)
        self.reaction_message = message
        self.game.reaction_messages.append(self.reaction_message)
        self.reaction_message_actions = kwargs

    async def draw_community_chest(self):
        self.reaction_message = None
        embed = discord.Embed(title="Community Chest Card", colour=discord.Colour.blue())
        card = random.randint(1, 18)
        if card == 1:
            embed.description = "Life Insurance Matures\nCollect M100"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(100), "Collect")
            })
        elif card == 2:
            self.set_square(0)
            self.passed_go = True
            embed.description = "Advance to GO\nCollect M200"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Advance")
            })
        elif card == 3:
            embed.description = "Pay hospital fees of M100"
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(100), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })
        elif card == 4:
            embed.description = "Holiday Fund Matures\nReceive M100"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(100), "Receive")
            })
        elif card == 5:
            embed.description = "Pay school fees of M50"
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(50), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })
        elif card == 6:
            embed.description = "Income Tax Refund\nCollect M20"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(20), "Collect")
            })
        elif card == 7:
            embed.description = "You inherit M100"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(100), "Collect")
            })
        elif card == 8:
            embed.description = "Doctor's fee\nPay M50"
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(50), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })
        elif card == 9:
            if self.game.chest_has_jail_card:
                embed.description = "Get Out of Jail Free\n\nThis card my be kept until needed, or sold"
                await self.create_reaction_message(embed, **{
                    "\N{WHITE HEAVY CHECK MARK}": (self.take_community_goojfc(), "Take")
                })
            else:
                await self.draw_community_chest()
        elif card == 10:
            embed.description = "From sale of stock you get M45"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(45), "Get")
            })
        elif card == 11:
            embed.description = "Receive M25 consultancy fee"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(25), "Receive")
            })
        elif card == 12:
            embed.description = "Grand Opera Opening\nCollect M50 from every player"
            await self.game.collect_from_everyone(self, 50)
        elif card == 13:
            embed.description = "Bank error in your favour\nCollect M200"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(200), "Collect")
            })
        elif card == 14:
            embed.description = "You have won second prize in a beauty contest\nCollect M10"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(10), "Collect")
            })
        elif card == 15:
            embed.description = "GO TO JAIL\nGo directly to jail\nDo not pass GO\nDo not collect M200"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.go_to_jail(), "Go")
            })
        elif card == 16:
            embed.description = "You are assessed for street repairs\nM40 per house\nM115 per hotel"
            total = 40 * self.num_houses() + 115 * self.num_hotels()
            embed.add_field(name="Total", value=str(total), inline=False)
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(total), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })
        elif card == 17:
            embed.description = "It is your birthday\nCollect M10 from every player"
            await self.game.collect_from_everyone(self, 10)
        elif card == 18:
            embed.description = "Pay hospital fees of M100"
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(100), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })

    async def draw_chance(self):
        embed = discord.Embed(title="Chance Card", colour=discord.Colour.orange())
        card = random.randint(1, 15)
        if card == 1:
            self.set_square(0)
            self.passed_go = True
            embed.description = "Advance to GO\nCollect M200"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Advance")
            })
        elif card == 2:
            if self.square >= 24:
                self.passed_go = True
            self.set_square(24)
            embed.description = "Advance to Trafalgar Square\nIf you pass GO, collect M200"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Advance")
            })
        elif card == 3:
            self.set_square(39)
            embed.description = "Advance to Mayfair"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Advance")
            })
        elif card == 4:
            if self.square >= 11:
                self.passed_go = True
            self.set_square(11)
            embed.description = "Advance to Pall Mall\nIf you pass GO, collect M200"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Advance")
            })
        elif card == 5:
            if self.square >= 35:
                self.passed_go = True
            self.set_square(((self.square + 5) % 10) + 5)
            self.double_rent = True
            embed.description = "Advance to the nearest Station\nIf unowned, you may buy it from the bank\nIf owned, pay twice the usual rent"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Advance")
            })
        elif card == 6:
            if self.square < 12:
                self.set_square(12)
            elif self.square < 28:
                self.set_square(28)
            else:
                self.passed_go = True
                self.set_square(12)
            self.set_square(((self.square + 5) % 10) + 5)
            self.double_rent = True
            embed.description = "Advance to the nearest Utation\nIf unowned, you may buy it from the bank\nIf owned, pay ten times the amount thrown"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Advance")
            })
        elif card == 7:
            embed.description = "Bank pays you dividend of M50"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(50), "Receive")
            })
        elif card == 8:
            if self.game.chance_has_jail_card:
                embed.description = "Get Out of Jail Free\n\nThis card my be kept until needed, or sold"
                await self.create_reaction_message(embed, **{
                    "\N{WHITE HEAVY CHECK MARK}": (self.take_chance_goojfc(), "Take")
                })
            else:
                await self.draw_community_chest()
        elif card == 9:
            self.move(-3)
            embed.description = "Go back three spaces"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Go back")
            })
        elif card == 10:
            embed.description = "GO TO JAIL\nGo directly to jail\nDo not pass GO\nDo not collect M200"
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.go_to_jail(), "Go")
            })
        elif card == 11:
            embed.description = "Make general repairs on all your property\nFor each house pay M25\nFor each hotel pay M100"
            total = 25 * self.num_houses() + 100 * self.num_hotels()
            embed.add_field(name="Total", value=f"M{total}", inline=False)
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(total), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })
        elif card == 12:
            embed.description = "Speeding fine M15"
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(15), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })
        elif card == 13:
            embed.description = "Take a trip to Kings Cross Station\nIf you pass GO, collect M200"
            if self.square >= 5:
                self.passed_go = True
            self.set_square(5)
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.evaluate_square(), "Take a trip")
            })
        elif card == 14:
            embed.description = "You have been elected Chairman of the Board\nPay each player M50"
            total = 50 * (len(self.game.monopoly_players) - 1)
            embed.add_field(name="Total", value=f"M{total}", inline=False)
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.elected_chairman(), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })
        elif card == 15:
            embed.description = "Your building loan matures\nCollect M150"
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.deposit(150), "Collect")
            })

    async def elected_chairman(self):
        if self.withdraw(50 * (len(self.game.monopoly_players) - 1)):
            self.reaction_message = None
            for player in self.game.monopoly_players:
                if player != self:
                    player.deposit(50)
            await self.confirm_end_turn()

    def num_houses(self):
        result = 0
        for prop in self.game.properties:
            p = self.game.properties[prop]
            if p.owner == self:
                result += p.houses
        return result

    def num_hotels(self):
        result = 0
        for prop in self.game.properties:
            p = self.game.properties[prop]
            if p.owner == self:
                result += p.hotel
        return result

    async def take_community_goojfc(self):
        self.game.chest_has_jail_card = False
        self.chest_jail_card = True
        await self.confirm_end_turn()

    async def take_chance_goojfc(self):
        self.game.chance_has_jail_card = False
        self.chance_jail_card = True
        await self.confirm_end_turn()

    async def go_to_jail(self):
        self.reaction_message = None
        self.set_square("jail")
        self.double_count = 0
        embed = discord.Embed(title="", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        self.game.board.update()
        await self.game.board.display(embed)
        embed = discord.Embed(title="JAIL", description="IN JAIL", colour=discord.Colour.dark_gray())
        await self.game.channel.send(embed=embed)
        await self.confirm_end_turn()

    async def jail_update(self):
        embed = discord.Embed(title="IN JAIL", description=f"{3-self.turns_in_jail} rolls left to escape", colour=self.colour)
        embed.add_field(name="React", value="\N{GAME DIE}\n\N{BANKNOTE WITH DOLLAR SIGN}\n\N{TICKET}")
        embed.add_field(name="Action", value="Attempt to roll doubles\nPay the M50 fine\nUse the Get Out of Jail Free Card")
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        self.jail_message = await self.game.channel.send(embed=embed)
        await self.jail_message.add_reaction("\N{GAME DIE}")
        await self.jail_message.add_reaction("\N{BANKNOTE WITH DOLLAR SIGN}")
        await self.jail_message.add_reaction("\N{TICKET}")
        self.game.reaction_messages.append(self.jail_message)

    async def jail_choice(self, choice):
        if choice == "roll" and not self.turns_in_jail == 3:
            self.game.reaction_messages.remove(self.jail_message)
            self.jail_message = None
            roll1 = random.randint(1, 6)
            roll2 = random.randint(1, 6)
            await self.rolled(roll1, roll2)
            if roll1 == roll2:
                self.set_square(10)
                self.turns_in_jail = 0
                self.move(roll1 + roll2)
                await self.evaluate_square()
            else:
                self.turns_in_jail += 1
                if self.turns_in_jail == 3:
                    embed = discord.Embed(title="Must Pay", description="Failed 3 attempts", colour=self.colour)
                    embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                    await self.create_reaction_message(embed, **{
                        "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(50), "Pay"),
                        "\N{CROSS MARK}": (self.declare_banbkruptcy(), "Declare bankruptcy")
                    })
                else:
                    self.game.turn += 1
                    self.game.turn %= len(self.game.monopoly_players)
                    await self.confirm_end_turn()
        elif choice == "pay":
            if await self.withdraw(50):
                self.set_square(10)
                self.game.reaction_messages.remove(self.jail_message)
                self.jail_message = None
                self.turns_in_jail = 0
                if self.turns_in_jail == 3:
                    self.move(self.roll)
                    await self.evaluate_square()
                else:
                    await self.game.new_turn()
        elif choice == "card" and not self.turns_in_jail == 3:
            if self.chest_jail_card or self.chance_jail_card:
                self.game.reaction_messages.remove(self.jail_message)
                self.jail_message = None
                if self.chest_jail_card:
                    self.chest_jail_card = False
                    self.game.chest_has_jail_card = True
                else:
                    self.chance_jail_card = False
                    self.game.chance_has_jail_card = True
                self.set_square(10)
                self.turns_in_jail = 0
                await self.game.new_turn()

    async def deposit(self, amount):
        self.balance += amount
        embed = discord.Embed(title="Deposited", description=f"M{amount}", colour=self.colour)
        embed.add_field(name="New Balance", value=f"M{self.balance}")
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
        if self.reaction_message:
            self.game.reaction_messages.remove(self.reaction_message)
            self.reaction_message = None
            await self.confirm_end_turn()

    async def withdraw(self, amount):
        if self.balance - amount >= 0:
            self.balance -= amount
            embed = discord.Embed(title="Withdrew", description=f"M{amount}", colour=self.colour)
            embed.add_field(name="New Balance", value=f"M{self.balance}")
            embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
            await self.game.channel.send(embed=embed)
            if self.reaction_message:
                self.game.reaction_messages.remove(self.reaction_message)
                self.reaction_message = None
                await self.confirm_end_turn()
            return True
        embed = discord.Embed(title="Insufficient Funds", description=f"M{amount} withdrawal failed", colour=self.colour)
        embed.add_field(name="Current Balance", value=f"M{self.balance}")
        embed.add_field(name="Aquire Funds", value="todo")
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
        return False

    async def declare_bankruptcy(self):
        if self.balance >= self.owe_amount:
            embed = discord.Embed(title="Not Bankrupt", description="You have enough money to pay", colour=self.colour)
            embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
            await self.game.channel.send(embed=embed)
            return False
        else:
            for prop in self.game.property:
                p = self.game.property[prop]
                if not p.mortgaged:
                    embed = discord.Embed(title="Not Bankrupt", description="You still have unmortgaged property", colour=self.colour)
                    embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                    await self.game.channel.send(embed=embed)
                    return False
                    break
            else:
                cash = self.balance
                props = list(filter(lambda p: p.owner == self, self.game.properties.values()))
                await self.withdraw(cash)
                embed = discord.Embed(title="Is Bankrupt", colour=self.colour)
                embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
                await self.game.channel.send(embed=embed)
                self.game.confirm_bankrupt(self)
                if self.owes:
                    await self.owes.deposit(cash)
                    await self.owes.receive_property(props)
                else:
                    await self.game.auction_properties(props)
                return True

    async def receive_property(self, props):
        interest = 0
        for prop in props:
            prop.set_owner(self)
            embed = discord.Embed(title="Received a Property", description=prop.name, colour=self.colour)
            embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
            if prop.mortgaged:
                interest += prop.price//20
        if interest:
            embed = discord.Embed(title="You Must Pay Interest on the Mortgaged Properties You Received")
            embed.add_field(name="Total", value=f"M{interest}", inline=False)
            await self.create_reaction_message(embed, **{
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.withdraw(interest), "Pay"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })

    async def buy(self, improvement, group, property):
        houseable_props = {}
        hotelable_props = {}
        for g in MonopolyProperty.groups:
            if self.owns_group(g):
                houseable_props[g] = []
                hotelable_props[g] = []
                for prop in self.game.property_group(g):
                    if prop.can_buy_house():
                        houseable_props[g].append(prop)
                    if prop.can_buy_hotel():
                        hotelable_props[g].append(prop)
                if not houseable_props[g]:
                    del houseable_props[g]
                if not hotelable_props[g]:
                    del hotelable_props[g]
        show_house = False
        show_hotel = False
        show_group = False
        if not improvement:
            embed = discord.Embed(title="Attempted Purchase", description="Specify an improvement, group and/or property\n\
                ```!bm buy <house/hotel> <group/all> <property/all>```")
            show_house = True
            show_hotel = True
        elif improvement not in ("house", "hotel"):
            embed = discord.Embed(title="Attempted Purchase", description="That is not a valid improvement\n\
                ```!bm buy <house/hotel> <group/all> <property/all>```")
            show_house = True
            show_hotel = True
        elif not group:
            embed = discord.Embed(title="Attempted Purchase", description="Specify a group and/or property\n\
                ```!bm buy <improvement> <group/all> <property/all>```")
            {"house": show_house, "hotel": show_hotel}[improvement] = True
        elif group == "all":
            props = []
            if improvement == "house":
                list(map(props.extend, houseable_props.values()))
                if props:
                    await self.confirm_improvement(0, "house", props)
                else:
                    embed = discord.Embed(title="Attempted Purchase", description="No valid properties")
            else:
                list(map(props.extend, hotelable_props.values()))
                if props:
                    await self.confirm_improvement(0, "hotel", props)
                else:
                    embed = discord.Embed(title="Attempted Purchase", description="No valid properties")
        elif (int(group) - 1) not in range(len({"house": houseable_props, "hotel": hotelable_props}[improvement])):
            embed = discord.Embed(title="Attempted Purchase", description="Invalid group")
            {"house": show_house, "hotel": show_hotel}[improvement] = True
        elif not property:
            embed = discord.Embed(title="Attempted Purchase", description="Specify a property\n\
                ```!bm buy <improvement> <group/all> <property/all>```")
            {"house": show_house, "hotel": show_hotel}[improvement] = True
            show_group = True
        elif property == "all":
            if improvement == "house":
                for i, g in enumerate(houseable_props):
                    if i == int(group):
                        group = g
                await self.confirm_improvement(0, "house", houseable_props[group])
            else:
                for i, g in enumerate(houseable_props):
                    if i == int(group):
                        group = g
                await self.confirm_improvement(0, "hotel", hotelable_props[group])
        else:
            if improvement == "house":
                for i, g in enumerate(houseable_props):
                    if i + 1== int(group):
                        group = g
            else:
                for i, g in enumerate(hotelable_props):
                    if i + 1 == int(group):
                        group = g
            if (int(property) - 1) not in range(len({"house": houseable_props, "hotel": hotelable_props}[improvement][group])):
                embed = discord.Embed(title="Attempted Purchase", description="Invalid property\n\
                    ```!bm buy <improvement> <group/all> <property/all>```")
                {"house": show_house, "hotel": show_hotel}[improvement] = True
                show_group = True
            else:
                if improvement == "house":
                    await self.confirm_improvement(0, "house", [houseable_props[group][int(property)-1]])
                else:
                    await self.confirm_improvement(0, "hotel", [hotelable_props[group][int(property)-1]])
        if show_house:
            if show_group:
                group_str = ""
                for i, prop in enumerate(houseable_props[group]):
                    group_str += f"{i+1:<3} - {prop.name}"
                embed.add_field(name=group, value = group_str)
            else:
                if not houseable_props:
                    embed.add_field(name="Groups and Properties with Purchaseable Houses", value="None", inline=False)
                else:
                    embed.add_field(name="Groups and Properties with Purchaseable Houses", value="-", inline=False)
                    for i, g in enumerate(houseable_props):
                        group_str = ""
                        for j, prop in enumerate(houseable_props[g]):
                            group_str += f"{j+1:<3} - {prop.name}\n"
                        embed.add_field(name=f"{i+1}. {g}", value=group_str)
        if show_hotel:
            if show_group:
                group_str = ""
                for i, prop in enumerate(hotelable_props[group]):
                    group_str += f"{i+1:<3} - {prop.name}"
                embed.add_field(name=group, value = group_str)
            else:
                if not hotelable_props:
                    embed.add_field(name="Groups and Properties with Purchaseable Hotels", value="None", inline=False)
                else:
                    embed.add_field(name="Groups and Properties with Purchaseable Hotels", value="-", inline=False)
                    for i, g in enumerate(hotelable_props):
                        group_str = ""
                        for j, prop in enumerate(hotelable_props[g]):
                            group_str += f"{j+1:<3} - {prop.name}\n"
                        embed.add_field(name=f"{i+1}. {g}", value=group_str)
        embed.colour = self.colour
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)

    async def sell(self, improvement, group, property):
        pass
    
    async def confirm_improvement(self, buy_or_sell, improvement, property):
        title = ("Confirm Purchase", "Confirm Sale")[buy_or_sell]
        embed = discord.Embed(title=title, colour=self.colour)
        embed.add_field(name="Improvement", value=improvement.capitalize(), inline=False)
        embed.add_field(name="Property", value="\n".join(map(lambda p: p.name, property)), inline=False)
        price = sum(map(lambda p: (p.house_price, p.house_price//2)[buy_or_sell], property))
        embed.add_field(name="Price", value=str(price), inline=False)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        self.confirming_improvement = (buy_or_sell, improvement, property, price)
        self.confirm_improvement_message = await self.game.channel.send(embed=embed)
        await self.confirm_improvement_message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await self.confirm_improvement_message.add_reaction("\N{CROSS MARK}")
        self.game.reaction_messages.append(self.confirm_improvement_message)

    async def confirmed_improvement(self, confirm):
        if confirm:
            if not self.confirming_improvement[0]:
                if await self.withdraw(self.confirming_improvement[3]):
                    embed = discord.Embed(title="Purchase Successful")
                    if self.confirming_improvement[1] == "house":
                        for p in self.confirming_improvement[2]:
                            p.houses += 1
                    else:
                        for p in self.confirming_improvement[2]:
                            p.houses = 0
                            p.hotel = True
                else:
                    return False
            else:
                await self.deposit(self.confirming_improvement[3])
                embed = discord.Embed(title="Sale Successful")
                if self.confirming_improvement[1] == "house":
                    for p in self.confirming_improvement[2]:
                        p.houses -= 1
                else:
                    for p in self.confirming_improvement[2]:
                        p.hotel = False
                        p.houses = 4
        else:
            if not self.confirming_improvement[0]:
                embed = discord.Embed(title="Purchase Cancelled")
            else:
                embed = discord.Embed(title="Sale Cancelled")
        self.game.reaction_messages.remove(self.confirm_improvement_message)
        self.confirm_improvement_message = None
        embed.colour = self.colour
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)

    async def mortgage(self, property):
        mortgageable = []
        for prop in self.game.properties:
            p = self.game.properties[p]
            if p.owner == self and p.houses == 0 and not p.hotel and not p.mortgaged:
                mortgageable.append(p)
        if not property:
            embed = discord.Embed(title="Mortgage", description = "```!bm mortgage <property>```")
        elif (property - 1) not in range(len(mortgageable)):
            embed = discord.Embed(title="Attempted Mortgage", description="Invalid property\n\
                ```!bm mortgage <property>```")
        else:
            embed = discord.Embed(title="Confirm Mortgage")
            embed.add_field(title="Property", value=mortgageable[property-1].name, inline=False)
            embed.add_field(title="Value", value=f"M{mortgageable[property-1].price//2}", inline=False)
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.confirm_mortgage[mortgageable[property-1]], "Mortgage property"),
                "\N{CROSS MARK}": (self.cancel_mortgage(), "Cancel")
            })
            return True
        prop_list = "None"
        if mortgageable:
            prop_list = ""
            value_list = ""
            for i, p in enumerate(mortgageable):
                prop_list += f"{i:<3} - {p.name}"
                value_list += f"M{p.price//2:>3}"
        embed.add_field(title="Mortgageable Properties", value=prop_list)
        if mortgageable:
            embed.add_field(title="Value", value=value_list)
        embed.colour = self.colour
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
    
    async def confirm_mortgage(self, property):
        if property.owner == self:
            await property.mortgage()
        
    async def cancel_mortgage(self):
        embed = discord.Embed(title="Mortgage Cancelled", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)

    async def rolled(self, roll1, roll2):
        self.roll = roll1 + roll2
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
        for player in self.game.monopoly_players:
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
            return await self.game.channel.send(embed=embed, file=file)
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
        if self.houses < 4 and self.owner.owns_group(self.group):
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
        self.mortgage = True
        await self.display()
        await self.owner.deposit(self.price//2)

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

    @command()
    async def bid(self, ctx, amount: int):
        for game in games:
            if type(game) == MonopolyGame and game.auction_message:
                for player in game.auction_participants:
                    if player.user == ctx.author:
                        await game.bid(player, amount)

    @command()
    async def buy(self, ctx, improvement: str=None, group: str=None, property: str=None):
        for game in games:
            if type(game) == MonopolyGame:
                for player in game.monopoly_players:
                    if player.user == ctx.author:
                        await player.buy(improvement, group, property)

    @command()
    async def sell(self, ctx, improvement: str=None, group: str=None, property: str=None):
        for game in games:
            if type(game) == MonopolyGame:
                for player in game.monopoly_players:
                    if player.user == ctx.author:
                        await player.sell(improvement, group, property)