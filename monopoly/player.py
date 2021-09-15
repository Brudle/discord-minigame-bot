import discord
from PIL import Image
import random

from game import Player
from monopoly.models import MonopolyProperty

class MonopolyPlayer(Player):

    def __init__(self, user, game):
        super().__init__(self, user, game)
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
        self.rolls = 0
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
        self.receiving_property = False

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
        if self.receiving_property:
            embed = discord.Embed(title="Still Receiving Property", colour=self.colour)
            embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
            await self.game.channel.send(embed=embed)
            return False
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
            elif prop.owner == self or prop.mortgaged:
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
            embed.description = "Advance to the nearest Utility\nIf unowned, you may buy it from the bank\nIf owned, pay ten times the amount thrown"
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
            total = 50 * (len(self.game.players) - 1)
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
        if self.withdraw(50 * (len(self.game.players) - 1)):
            self.reaction_message = None
            for player in self.game.players:
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
                self.game.turn += 1
                self.game.turn %= len(self.game.players)
                await self.move(roll1 + roll2)
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
                    self.game.turn %= len(self.game.players)
                    await self.confirm_end_turn()
        elif choice == "pay":
            if await self.withdraw(50):
                self.set_square(10)
                self.game.reaction_messages.remove(self.jail_message)
                self.jail_message = None
                self.turns_in_jail = 0
                if self.turns_in_jail == 3:
                    self.game.turn += 1
                    self.game.turn %= len(self.game.players)
                    await self.move(self.roll)
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
        if props:
            self.receiving_property = True
            self.receiving_properties = props
            self.property_currently_receiving = 0
            await self.receive_property_update()

    async def receive_property_update(self):
        prop = self.receiving_properties[self.property_currently_receiving]
        prop.set_owner(self)
        embed = discord.Embed(title="Received a Property", description=prop.name, colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        if prop.mortgaged:
            embed.add_field(name="Recieved a Mortgaged Property", value="You must either unmortage this property or pay additional interest", inline=False)
            embed.add_field(name="Unmortgage Cost", value=f"M{(prop.price//20)*11}", inline=False)
            embed.add_field(name="Interest Payment", value=f"M{prop.price//20}", inline=False)
            await self.create_reaction_message(embed, **{
                "\N{MONEY BAG}": (self.received_property(prop, "unmortgage"), "Unmortgage"),
                "\N{BANKNOTE WITH DOLLAR SIGN}": (self.received_property(prop, "interest"), "Pay interest"),
                "\N{CROSS MARK}": (self.declare_bankruptcy(), "Declare bankruptcy")
            })
        else:
            await self.game.channel.send(embed=embed)
            self.property_currently_receiving += 1
            if self.property_currently_receiving >= len(self.receiving_properties):
                self.receiving_property = False
                if self.game.current_turn == self and self.rolled_this_turn and not self.double_count:
                    await self.confirm_end_turn()
            else:
                await self.receive_property_update()

    async def received_property(self, prop, choice):
        if choice == "interest":
            if not await self.withdraw(prop.price//20):
                return False
        elif choice == "unmortgage":
            if not await self.withdraw((prop.price//20)*11):
                return False
            prop.unmortgage()
        self.reaction_message = None
        self.property_currently_receiving += 1
        if self.property_currently_receiving >= len(self.receiving_properties):
            self.receiving_property = False
            if self.game.current_turn == self and self.rolled_this_turn and not self.double_count:
                await self.confirm_end_turn()
        else:
            await self.receive_property_update()

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
                    if i + 1 == int(group):
                        group = g
                await self.confirm_improvement(0, "house", houseable_props[group])
                return True
            else:
                for i, g in enumerate(hotelable_props):
                    if i + 1 == int(group):
                        group = g
                await self.confirm_improvement(0, "hotel", hotelable_props[group])
                return True
        else:
            if improvement == "house":
                for i, g in enumerate(houseable_props):
                    if i + 1 == int(group):
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
                    return True
                else:
                    await self.confirm_improvement(0, "hotel", [hotelable_props[group][int(property)-1]])
                    return True
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
        houseable_props = {}
        hotelable_props = {}
        for g in MonopolyProperty.groups:
            if self.owns_group(g):
                houseable_props[g] = []
                hotelable_props[g] = []
                for prop in self.game.property_group(g):
                    if prop.can_sell_house():
                        houseable_props[g].append(prop)
                    if prop.can_sell_hotel():
                        hotelable_props[g].append(prop)
                if not houseable_props[g]:
                    del houseable_props[g]
                if not hotelable_props[g]:
                    del hotelable_props[g]
        show_house = False
        show_hotel = False
        show_group = False
        if not improvement:
            embed = discord.Embed(title="Attempted Sale", description="Specify an improvement, group and/or property\n\
                ```!bm sell <house/hotel> <group/all> <property/all>```")
            show_house = True
            show_hotel = True
        elif improvement not in ("house", "hotel"):
            embed = discord.Embed(title="Attempted Sale", description="That is not a valid improvement\n\
                ```!bm sell <house/hotel> <group/all> <property/all>```")
            show_house = True
            show_hotel = True
        elif not group:
            embed = discord.Embed(title="Attempted Sale", description="Specify a group and/or property\n\
                ```!bm sell <improvement> <group/all> <property/all>```")
            {"house": show_house, "hotel": show_hotel}[improvement] = True
        elif group == "all":
            props = []
            if improvement == "house":
                list(map(props.extend, houseable_props.values()))
                if props:
                    await self.confirm_improvement(1, "house", props)
                else:
                    embed = discord.Embed(title="Attempted Sale", description="No valid properties")
            else:
                list(map(props.extend, hotelable_props.values()))
                if props:
                    await self.confirm_improvement(1, "hotel", props)
                else:
                    embed = discord.Embed(title="Attempted Sale", description="No valid properties")
        elif (int(group) - 1) not in range(len({"house": houseable_props, "hotel": hotelable_props}[improvement])):
            embed = discord.Embed(title="Attempted Sale", description="Invalid group")
            {"house": show_house, "hotel": show_hotel}[improvement] = True
        elif not property:
            embed = discord.Embed(title="Attempted Sale", description="Specify a property\n\
                ```!bm sell <improvement> <group/all> <property/all>```")
            {"house": show_house, "hotel": show_hotel}[improvement] = True
            show_group = True
        elif property == "all":
            if improvement == "house":
                for i, g in enumerate(houseable_props):
                    if i + 1 == int(group):
                        group = g
                await self.confirm_improvement(1, "house", houseable_props[group])
                return True
            else:
                for i, g in enumerate(hotelable_props):
                    if i + 1 == int(group):
                        group = g
                await self.confirm_improvement(1, "hotel", hotelable_props[group])
                return True
        else:
            if improvement == "house":
                for i, g in enumerate(houseable_props):
                    if i + 1 == int(group):
                        group = g
            else:
                for i, g in enumerate(hotelable_props):
                    if i + 1 == int(group):
                        group = g
            if (int(property) - 1) not in range(len({"house": houseable_props, "hotel": hotelable_props}[improvement][group])):
                embed = discord.Embed(title="Attempted Sale", description="Invalid property\n\
                    ```!bm sell <improvement> <group/all> <property/all>```")
                {"house": show_house, "hotel": show_hotel}[improvement] = True
                show_group = True
            else:
                if improvement == "house":
                    await self.confirm_improvement(1, "house", [houseable_props[group][int(property)-1]])
                    return True
                else:
                    await self.confirm_improvement(1, "hotel", [hotelable_props[group][int(property)-1]])
                    return True
        if show_house:
            if show_group:
                group_str = ""
                for i, prop in enumerate(houseable_props[group]):
                    group_str += f"{i+1:<3} - {prop.name}"
                embed.add_field(name=group, value = group_str)
            else:
                if not houseable_props:
                    embed.add_field(name="Groups and Properties with Sellable Houses", value="None", inline=False)
                else:
                    embed.add_field(name="Groups and Properties with Sellable Houses", value="-", inline=False)
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
                    embed.add_field(name="Groups and Properties with Sellable Hotels", value="None", inline=False)
                else:
                    embed.add_field(name="Groups and Properties with Sellable Hotels", value="-", inline=False)
                    for i, g in enumerate(hotelable_props):
                        group_str = ""
                        for j, prop in enumerate(hotelable_props[g]):
                            group_str += f"{j+1:<3} - {prop.name}\n"
                        embed.add_field(name=f"{i+1}. {g}", value=group_str)
        embed.colour = self.colour
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
    
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
        await self.confirm_end_turn()

    async def mortgage(self, property):
        mortgageable = []
        for prop in self.game.properties:
            p = self.game.properties[prop]
            if p.owner == self and p.houses == 0 and not p.hotel and not p.mortgaged:
                mortgageable.append(p)
        if not property:
            embed = discord.Embed(title="Mortgage", description = "```!bm mortgage <property>```")
        elif (property - 1) not in range(len(mortgageable)):
            embed = discord.Embed(title="Attempted Mortgage", description="Invalid property\n\
                ```!bm mortgage <property>```")
        else:
            embed = discord.Embed(title="Confirm Mortgage")
            embed.add_field(name="Property", value=mortgageable[property-1].name, inline=False)
            embed.add_field(name="Value", value=f"M{mortgageable[property-1].price//2}", inline=False)
            await self.create_reaction_message(embed, **{
                "\N{MONEY WITH WINGS}": (self.confirm_mortgage(mortgageable[property-1]), "Mortgage property"),
                "\N{CROSS MARK}": (self.cancel_mortgage(), "Cancel")
            })
            return True
        prop_list = "None"
        if mortgageable:
            prop_list = ""
            value_list = ""
            for i, p in enumerate(mortgageable):
                prop_list += f"{i+1:<3} - {p.name}\n"
                value_list += f"M{p.price//2:>3}\n"
        embed.add_field(name="Mortgageable Properties", value=prop_list)
        if mortgageable:
            embed.add_field(name="Value", value=value_list)
        embed.colour = self.colour
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
    
    async def confirm_mortgage(self, property):
        self.reaction_message = None
        if property.owner == self:
            await property.mortgage()
        
    async def cancel_mortgage(self):
        self.reaction_message = None
        embed = discord.Embed(title="Mortgage Cancelled", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
        await self.confirm_end_turn()

    async def unmortgage(self, property):
        mortgageable = []
        for prop in self.game.properties:
            p = self.game.properties[prop]
            if p.owner == self and p.mortgaged:
                mortgageable.append(p)
        if not property:
            embed = discord.Embed(title="Unmortgage", description = "```!bm unmortgage <property>```")
        elif (property - 1) not in range(len(mortgageable)):
            embed = discord.Embed(title="Attempted Unmortgage", description="Invalid property\n\
                ```!bm unmortgage <property>```")
        else:
            embed = discord.Embed(title="Confirm Unmortgage")
            embed.add_field(name="Property", value=mortgageable[property-1].name, inline=False)
            embed.add_field(name="Value", value=f"M{mortgageable[property-1].price//20}")
            embed.add_field(name="Interest", value=f"M{mortgageable[property-1].price//20}")
            embed.add_field(name="Total Price", value=f"M{(mortgageable[property-1]//20)*11}")
            await self.create_reaction_message(embed, **{
                "\N{MONEY BAG}": (self.confirm_unmortgage(mortgageable[property-1]), "Unmortgage property"),
                "\N{CROSS MARK}": (self.cancel_unmortgage(), "Cancel")
            })
            return True
        prop_list = "None"
        if mortgageable:
            prop_list = ""
            value_list = ""
            for i, p in enumerate(mortgageable):
                prop_list += f"{i+1:<3} - {p.name}\n"
                value_list += f"M{(p.price//20)*11:>3}\n"
        embed.add_field(name="Mortgageable Properties", value=prop_list)
        if mortgageable:
            embed.add_field(name="Price", value=value_list)
        embed.colour = self.colour
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
    
    async def confirm_unmortgage(self, property):
        if property.owner == self:
            if await self.withdraw((property.price//20)*11):
                self.reaction_message = None
                await property.unmortgage()
                await self.confirm_end_turn()
        
    async def cancel_unmortgage(self):
        self.reaction_message = None
        embed = discord.Embed(title="Unmortgage Cancelled", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)
        await self.confirm_end_turn()

    async def trade(self, user):
        for player in self.game.players:
            if player.user == user:
                self.trading_with = player
                break
        else:
            return False
        self.trade_offering = [0, [], 0]
        self.trade_asking = [0, [], 0]
        await self.trade_update()

    async def trade_update(self):
        embed = discord.Embed(title="Trade", colour=self.colour)
        embed.add_field(name="Available to Trade\n\nYour Cash", value=f"M{self.balance}", inline=False)
        prop_str = "\n".join(f"{i+1:<3} - {p.name}" for i, p in enumerate(
            list(filter(lambda p: p.owner == self and p not in self.trade_offering[1] and not p.houses and not p.hotel, self.game.properties.values()))))
        embed.add_field(name="Your Property", value=prop_str or "None", inline=False)
        embed.add_field(name="Your Get Out of Jail Free Cards", value=str(len(list(filter(None, [self.chest_jail_card, self.chance_jail_card])))), inline=False)
        embed.add_field(name=f"{self.trading_with.user.name}'s Cash", value=f"M{self.trading_with.balance}", inline=False)
        prop_str = "\n".join(f"{i+1:<3} - {p.name}" for i, p in enumerate(
            list(filter(lambda p: p.owner == self.trading_with and p not in self.trade_asking[1] and not p.houses and not p.hotel, self.game.properties.values()))))
        embed.add_field(name=f"{self.trading_with.user.name}'s Property", value=prop_str or "None", inline=False)
        embed.add_field(name=f"{self.trading_with.user.name}'s Get Out of Jail Free Cards",
        value=str(len(list(filter(None, [self.trading_with.chest_jail_card, self.trading_with.chance_jail_card])))), inline=False)
        embed.add_field(name="Current Trade\n\nOffering Cash", value=f"M{self.trade_offering[0]}", inline=False)
        prop_str = "\n".join(f"{i+1:<3} - {p.name}" for i, p in enumerate(self.trade_offering[1]))
        embed.add_field(name="Offering Property", value=prop_str or "None", inline=False)
        embed.add_field(name="Offering Get Out of Jail Free Cards", value=str(self.trade_offering[2]), inline=False)
        embed.add_field(name="Asking Cash", value=f"M{self.trade_asking[0]}")
        prop_str = "\n".join(f"{i+1:<3} - {p.name}" for i, p in enumerate(self.trade_asking[1]))
        embed.add_field(name="Asking Property", value=prop_str or "None", inline=False)
        embed.add_field(name="Asking Get Out of Jail Free Cards", value=str(self.trade_asking[2]), inline=False)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        embed.set_footer(text=self.trading_with.user.name, icon_url=self.trading_with.user.avatar_url)
        if self.reaction_message:
            await self.reaction_message.edit(embed=embed)
        else:
            await self.create_reaction_message(embed, **{
                "\N{WHITE HEAVY CHECK MARK}": (self.trade_send(), "Send trade offer"),
                "\N{CROSS MARK}": (self.trade_cancel(), "Cancel trade")
            })

    async def trade_offer_cash(self, amount):
        if amount > 0 and amount <= self.balance:
            self.trade_offering[0] = amount
            await self.trade_update()

    async def trade_ask_cash(self, amount):
        if amount > 0 and amount < self.trading_with.balance:
            self.trade_asking[0] = amount
            await self.trade_update()

    async def trade_offer_add_property(self, property):
        for i, p in enumerate(list(filter(
            lambda p: p.owner == self and p not in self.trade_offering[1] and not p.houses and not p.hotel, self.game.properties.values()))):
            if i + 1 == property:
                self.trade_offering[1].append(p)
                await self.trade_update()
                break

    async def trade_offer_remove_property(self, property):
        for i, p in enumerate(self.trade_offering[1]):
            if i + 1 == property:
                self.trade_offering[1].remove(p)
                await self.trade_update()
                break

    async def trade_ask_add_property(self, property):
        for i, p in enumerate(list(filter(
            lambda p: p.owner == self.trading_with and p not in self.trade_asking[1] and not p.houses and not p.hotel, self.game.properties.values()))):
            if i + 1 == property:
                self.trade_asking[1].append(p)
                await self.trade_update()
                break

    async def trade_ask_remove_property(self, property):
        for i, p in enumerate(self.trade_asking[1]):
            if i + 1 == property:
                self.trade_asking[1].remove(p)
                await self.trade_update()
                break

    async def trade_offer_card(self, amount):
        if amount > 0 and amount <= len(list(filter(None, [self.chest_jail_card, self.chance_jail_card]))):
            self.trade_offering[2] == amount
            await self.trade_update()

    async def trade_ask_card(self, amount):
        if amount >0 and amount <= len(list(filter(None, [self.trading_with.chest_jail_card, self.trading_with.chance_jail_card]))):
            self.trade_asking[2] == amount
            await self.trade_update()

    async def trade_send(self):
        self.reaction_message = None
        await self.trading_with.trade_receive(self)

    async def trade_cancel(self):
        self.reaction_message = None
        embed = discord.Embed(title="Trade Cancelled", colour=self.colour)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        await self.game.channel.send(embed=embed)

    async def trade_receive(self, player):
        self.trading_with = player
        self.trade_offering = player.trade_asking
        self.trade_asking = player.trade_offering
        embed = discord.Embed(title="Received a Trade Offer", colour=self.colour)
        embed.add_field(name="Offering Cash", value=f"M{self.trade_asking[0]}", inline=False)
        prop_str = "\n".join(f"{p.name}" for p in self.trade_asking[1])
        embed.add_field(name="Offering Property", value=prop_str or "None", inline=False)
        embed.add_field(name="Offering Get Out of Jail Free Cards", value=str(self.trade_asking[2]), inline=False)
        embed.add_field(name="Asking Cash", value=f"M{self.trade_offering[0]}", inline=False)
        prop_str = "\n".join(f"{p.name}" for p in self.trade_offering[1])
        embed.add_field(name="Asking Property", value=prop_str or "None", inline=False)
        embed.add_field(name="Asking Get Out of Jail Free Cards", value=str(self.trade_offering[2]), inline=False)
        embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
        embed.set_footer(text=self.trading_with.user.name, icon_url=self.trading_with.user.avatar_url)
        await self.create_reaction_message(embed, **{
            "\N{WHITE HEAVY CHECK MARK}": (self.trade_accept(), "Accept trade"),
            "\N{CROSS MARK}": (self.trade_decline(), "Decline trade"),
            "\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}": (self.trade_counter(), "Make a counter offer")
        })

    async def trade_accept(self):
        self.reaction_message = None
        if self.trade_asking[0]:
            if not await self.trading_with.withdraw(self.trade_asking[0]):
                return False
            await self.deposit(self.trade_asking[0])
        if self.trade_offering[0]:
            if not await self.withdraw(self.trade_offering[0]):
                return False
            await self.trading_with.deposit(self.trade_offering[0])
        await self.receive_property(self.trade_asking[1])
        await self.trading_with.receive_property(self.trade_offering[1])
        if self.trade_asking[2] == 2:
            self.trading_with.chest_jail_card = False
            self.trading_with.chance_jail_card = False
            self.chest_jail_card = True
            self.chance_jail_card = True
        elif self.trade_offering[2] == 2:
            self.chest_jail_card = False
            self.chance_jail_card = False
            self.trading_with.chest_jail_card = True
            self.trading_with.chance_jail_card = True
        elif self.trade_asking[2] == 1:
            if self.trading_with.chest_jail_card:
                self.trading_with.chest_jail_card = False
                self.chest_jail_card = True
            elif self.trading_with.chance_jail_card:
                self.trading_with.chance_jail_card = False
                self.chance_jail_card = True
        elif self.trade_offering[2] == 1:
            if self.chest_jail_card:
                self.chest_jail_card = False
                self.trading_with.chest_jail_card = True
            elif self.chance_jail_card:
                self.chance_jail_card = False
                self.trading_with.chance_jail_card = True

    async def trade_decline(self):
        self.reaction_message = None

    async def trade_counter(self):
        self.reaction_message = None
        await self.trade_update()

    async def take_turn(self):
        self.rolled_this_turn = False
        self.double_count = 0
        embed = discord.Embed(title="Your Turn")
        embed, file = self.game.board.display(embed)
        await self.create_reaction_message(embed, {
            "\N{GAME DIE}": (self.roll(), "Roll the dice")
        }, file)

    async def roll(self):
        if not self.rolled_this_turn:
            self.reaction_message = None
            await self.rolled(random.randint(1, 6), random.randint(1, 6))
        if self.double_count == 3:
            embed = discord.Embed(title="Rolled doubles three times in a row!")
            await self.send_as_author(embed)
            await self.go_to_jail()
        else:
            await self.move(self.rolls)

    async def rolled(self, roll1, roll2):
        self.rolled_this_turn = True
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
        self.rolls = roll1 + roll2
        if roll1 == roll2:
            self.double_count += 1