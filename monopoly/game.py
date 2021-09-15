import discord
import random

from game import Game
from monopoly.player import MonopolyPlayer
from monopoly.models import MonopolyBoard, MonopolyProperty

class MonopolyGame(Game):

    def __init__(self, *args):
        super().__init__(*args, "Monopoly", minplayers=2, maxplayers=6)
        self.board = MonopolyBoard(self)
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

            self.properties[square] = MonopolyProperty(self, name, price, rent, group)

    async def play(self):
        temp_players = []
        for player in self.players:
            temp_players.append(MonopolyPlayer(player, self))
        self.players = temp_players
        self.choosing_colours = True
        embed = discord.Embed(title="Choose you colours", description="use ```!bm colour <colour>```")
        await self.channel.send(embed=embed)

    async def chose_colour(self, player, colour):
        for other in self.players:
            if other.colour == colour:
                await self.channel.send("that colour is taken")
                break
        else:
            player.set_colour(colour)
            embed = discord.Embed(title="Set their colour", colour=colour)
            embed.set_author(name=player.user.name, icon_url=player.user.avatar_url)
            await self.channel.send(embed=embed)

            for player in self.players:
                if not player.colour:
                    break
            else:
                self.choosing_colours = False
                # self.deciding_order = True
                # self.rolling = self.players.copy()
                # embed = discord.Embed(title="Roll for the turn order", description="click the die")
                # message = await self.channel.send(embed=embed)
                # await message.add_reaction("\N{GAME DIE}")
                # self.reaction_messages.append(message)
                for i, player in enumerate(self.players):
                    player.set_place(i)
                await self.new_turn()

    async def new_turn(self):
        self.current_turn = self.players[self.turn]
        await self.current_turn.take_turn()
        # embed = discord.Embed(title="Your Turn", colour=self.current_turn.colour)
        # embed.set_author(name=self.current_turn.user.name, icon_url=self.current_turn.user.avatar_url)
        # self.board.update()
        # message = await self.board.display(embed)
        # if self.current_turn.square == "jail":
        #     await self.current_turn.jail_update()
        # else:
        #     self.current_turn.rolled_this_turn = False
        #     self.rolling = [self.current_turn]
        #     await message.add_reaction("\N{GAME DIE}")
        #     self.reaction_messages.append(message)

    async def reaction_add(self, reaction, user):
        for player in self.players:
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
                    self.turn %= len(self.players)
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
        self.auction_participants = self.players.copy()
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
                if self.current_turn not in self.players:
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
        self.left_to_collect = list(filter(lambda p: p != player, self.players))
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
        self.players.remove(player)
        if len(self.players) == 1:
            embed = discord.Embed(title="Won the game!", colour=self.players[0].colour)
            embed.set_author(name=self.players[0].user.name, icon_url=self.players[0].user.avatar_url)