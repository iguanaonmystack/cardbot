#!/usr/bin/env python3

import sys
import random
from configparser import ConfigParser

from twisted.words.protocols.irc import IRCClient
from twisted.internet import reactor, protocol


class cardbotUser:
    def __init__(self, username, ident, realname):
        self.username = username
        self.ident = ident
        self.realname = realname

    def name(self):
        return self.username


# --------------------------------------------------------------------------


class cardbot(object):
    def __new__(self, _dealer):
        # FIXME - this is ridiculously hacky just to make the dealer dynamic.
        # I need to read the twisted docs sometime when I'm less asleep.
        class cardbot(IRCClient):

            cards = []
            players = []
            dealer = _dealer  # checks for this should be made case insensitive
            helpURL = "http://example.com/projects/cardbot.shtml"

            def __init__(self):
                self.nickname = "CardPack"
                self.realname = "this code still works??"

            def signedOn(self):
                self.mode(self.nickname, False, "x")
                self.join(self.factory.mainchannel)
                self.initialiseDeck(self.factory.mainchannel)

            def userJoined(self, user, channel):
                print("join: %s to %s" % (user, channel))

            def userLeft(self, user, channel):
                print("part: %s from %s" % (user, channel))

            def userRename(self, oldname, newname):
                print("nickchange: %s to %s" % (oldname, newname))
                player = getPlayer(oldname)
                if player is not None:
                    player.setName(newname)

            def kickedFrom(self, channel, kicker, msg):
                print("%s kicked me from %s (%s)" % (kicker, channel, msg))

            def privmsg(self, user, channel, msg):
                user = self.factory.getUserInfo(user)
                sender = user.name()
                print("<%s:%s> %s" % (user.name(), channel, msg))

                mlc = msg.lower()

                if self.nickname == channel:
                    # if channel is self.nickname, it's a PM.
                    params = mlc.split()
                    command = params[0]

                    if command == "showhand":
                        self.revealHand(sender, sender)
                    elif command == "showpicked":
                        self.revealPicked(sender, sender)
                    elif command == "pick":
                        self.pick(params[1], sender)
                    elif command == "unpick":
                        self.unpick(params[1], sender)
                    else:
                        self.msg(
                            sender,
                            "Unknown command. See "
                            + self.helpURL
                            + " for commands.",
                        )

                else:
                    # otherwise, it's in a channel.
                    params = mlc.split()
                    # words in lower case
                    try:
                        command = params[1]
                        # command in lower case
                    except IndexError:
                        command = ""

                    if mlc.startswith(self.nickname.lower()):
                        if command == "dealer":
                            self.setDealer(params[2], channel)
                        elif command == "reveal" or command == "showhand":
                            self.revealHand(sender, channel)
                        elif command == "showpicked":
                            self.revealPicked(sender, channel)
                        elif command == "giveback":
                            self.giveback(sender, channel)
                        elif command == "givehandto":
                            self.givehandto(sender, params[2], channel)
                        elif command == "help" or command == "about":
                            self.msg(
                                channel,
                                "See "
                                + self.helpURL
                                + " for details and commands.",
                            )
                        elif command == "offer":  # offer player numcards
                            self.offer(sender, params[2], params[3], channel)
                        elif command == "unoffer":
                            self.offer(sender, "", 0, channel)
                        elif command == "takefrom":
                            self.takefrom(sender, params[2], params[3:])

                    # in-channel, dealer only
                    if sender.lower() == self.dealer.lower():
                        if command == "reset":
                            self.resetGame(channel)
                        elif command == "addplayers":
                            i = 2
                            while i < len(params):
                                self.addPlayer(params[i], channel)
                                i = i + 1
                        elif command == "addplayer":
                            self.addPlayer(params[2], channel)
                        elif command == "remplayer":
                            self.remPlayer(params[2], channel)
                        elif command == "dealto":
                            if len(params) > 3:
                                self.dealTo(
                                    self.getPlayer(params[2]),
                                    int(params[3]),
                                    channel,
                                )
                            else:
                                self.dealTo(
                                    self.getPlayer(params[2]), 1, channel
                                )
                        elif command == "deal":
                            if len(params) > 2:
                                self.deal(int(params[2]), channel)
                            else:
                                self.deal(1, channel)
                        elif command == "play21":
                            self.deal(2, channel)

            def action(self, user, channel, msg):
                user = self.factory.getUserInfo(user)
                print("* %s %s" % (user.name(), msg))

            def noticed(self, user, channel, msg):
                pass

            def getPlayer(self, name):
                name = name.lower()
                for i in self.players:
                    if i.getName() == name:
                        return i
                return None

            def setDealer(self, dealer, channel):
                self.dealer = dealer
                self.msg(channel, "Dealer is set to " + dealer)

            def getDealer(self):
                return self.dealer

            def initialiseDeck(self, channel):
                self.cards = []
                for deck in [
                    card.CLUBS,
                    card.DIAMONDS,
                    card.HEARTS,
                    card.SPADES,
                ]:
                    for value in range(2, card.ACE + 1):
                        c = card(value, deck)
                        self.cards.append(c)
                self.msg(channel, "Shuffling deck...")
                self.shuffle()
                self.msg(channel, "...Done")

            def shuffle(self):
                packsize = len(self.cards)
                i = packsize - 1
                while i >= 0:
                    self.cards.append(self.cards.pop(random.randint(0, i)))
                    i = i - 1

            def resetGame(self, channel):
                self.initialiseDeck(channel)
                self.players = []
                self.msg(channel, "Reset complete")

            def addPlayer(self, name, channel):
                self.players.append(player(name))
                self.msg(channel, "Player " + name + " added")
                self.msg(name, "You are now in the card game at " + channel)

            def remPlayer(self, name, channel):
                p = self.getPlayer(name)
                if p is not None:
                    returnedcards = p.getPicked()
                    for i in returnedcards:
                        self.cards.append(i)
                    returnedcards = p.getHand()
                    for i in returnedcards:
                        self.cards.append(i)
                    self.players.remove(p)
                    self.msg(channel, "Player " + name + " removed")
                    self.msg(name, "You are no longer in the game")
                else:
                    self.msg(channel, name + " is not a player")

            def dealOne(self, p, channel):
                # this used to be another dealTo in the original Java version.
                if p is not None:
                    try:
                        c = self.cards.pop(0)
                        p.addToHand(c)
                        self.msg(
                            p.getName(),
                            "You have been dealt the " + c.toString(),
                        )
                    except Exception as e:
                        raise EmptyDeckError()

            def dealTo(self, p, numcards, channel):
                try:
                    for i in range(numcards):
                        try:
                            self.dealOne(p, channel)
                        except EmptyDeckError:
                            raise EmptyDeckError(i)
                    self.msg(
                        channel,
                        str(numcards)
                        + " cards have been dealt to "
                        + p.getName(),
                    )
                except EmptyDeckError as e:
                    self.msg(
                        channel,
                        "The pack has run out of cards. "
                        + str(e.value)
                        + " cards were dealt to "
                        + p.getName(),
                    )

            def deal(self, numcards, channel):
                for i in self.players:
                    self.dealTo(i, numcards, channel)

            def revealHand(self, name, channel):
                hand = self.getPlayer(name).getHand()
                returnstring = name + "'s hand is: "
                if len(hand) > 0:
                    for i in range(len(hand) - 1):
                        returnstring = returnstring + hand[i].toString() + "; "
                    returnstring = (
                        returnstring + hand[len(hand) - 1].toString() + "."
                    )
                else:
                    returnstring = returnstring + "empty"
                self.msg(channel, returnstring)

            def revealPicked(self, name, channel):
                hand = self.getPlayer(name).getPicked()
                returnstring = name + " has these cards picked: "
                if len(hand) > 0:
                    for i in range(len(hand) - 1):
                        returnstring = returnstring + hand[i].toString() + "; "
                    returnstring = (
                        returnstring + hand[len(hand) - 1].toString() + "."
                    )
                else:
                    returnstring = returnstring + "none"
                self.msg(channel, returnstring)

            def pick(self, cardID, sender):
                """cardID is the card to pick in the format [value][suitletter],
                    eg: 7C, 10H, AS"""

                c = self.getCardFromCardID(cardID)
                if c is None:
                    self.msg(sender, "That's not a valid card selection.")
                else:
                    if self.getPlayer(sender).pick(c) == True:
                        self.msg(
                            sender,
                            "You have picked out the " + c.toString() + ".",
                        )
                    else:
                        self.msg(
                            sender,
                            "You don't have the "
                            + c.toString()
                            + " in your hand.",
                        )

            def unpick(self, cardID, sender):
                """cardID is the card to pick in the format [value][suitletter],
                    eg: 7C, 10H, AS"""

                c = self.getCardFromCardID(cardID)
                if c is not None:
                    if self.getPlayer(sender).unpick(c) == True:
                        self.msg(
                            sender,
                            "You have unpicked the " + c.toString() + ".",
                        )
                    else:
                        self.msg(
                            sender,
                            "You don't have the "
                            + c.toString()
                            + " currently picked.",
                        )
                else:
                    self.msg(sender, "That's not a valid card selection.")

            def getCardFromCardID(self, cardID):
                """ cardID is the card to pick in the format [value][suitletter],
                    eg: 7C, 10H, AS"""
                value = -1
                if cardID[0] == 'a':
                    value = card.ACE
                elif cardID[0] == 'j':
                    value = card.JACK
                elif cardID[0] == 'q':
                    value = card.QUEEN
                elif cardID[0] == 'k':
                    value = card.KING
                elif cardID[0] == '1':
                    value = 10
                else:
                    try:
                        value = int(cardID[0])
                    except ValueError:
                        pass

                suit = -1
                if cardID[-1] == 'c':
                    suit = card.CLUBS
                elif cardID[-1] == 'd':
                    suit = card.DIAMONDS
                elif cardID[-1] == 'h':
                    suit = card.HEARTS
                elif cardID[-1] == 's':
                    suit = card.SPADES
                try:
                    c = card(value, suit)
                    return c
                except ValueError as e:
                    return None

            def giveback(self, name, channel):
                returnedcards = self.getPlayer(name).removePickedCards()
                for i in returnedcards:
                    self.cards.append(i)
                self.msg(
                    channel,
                    name
                    + " returned "
                    + str(len(returnedcards))
                    + " cards to the bottom of the deck.",
                )

            def givehandto(self, fromwhom, to, channel):
                p = self.getPlayer(fromwhom)
                if self.getPlayer(to) is not None:
                    self.msg(
                        channel,
                        fromwhom
                        + " tried to transfer their cards to "
                        + to
                        + ", but "
                        + to
                        + " is already a player",
                    )
                else:
                    p.setName(to)
                    self.msg(
                        channel,
                        fromwhom + " has transferred their cards to " + to,
                    )

            def offer(self, offerer, player, numcards, channel):
                o = self.getPlayer(offerer)
                p = self.getPlayer(player)
                o.offered = (numcards, p)
                if numcards != 0:
                    self.msg(
                        channel,
                        offerer
                        + " has offered "
                        + numcards
                        + " cards to "
                        + player,
                    )
                else:
                    self.msg(
                        channel, offerer + " has withdrawn their offer of cards"
                    )

            def takefrom(self, sender, cardgiver, cardslist):
                pass
                # to be written

        return cardbot


# --------------------------------------------------------------------------


class card:
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14  # arbitrary choice

    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3

    def __init__(self, value, suit):
        if value < 2 or value > self.ACE:
            raise ValueError("Card value out of range: " + str(value))
        if suit < self.CLUBS or suit > self.SPADES:
            raise ValueError("Suit value not valid:" + str(suit))
        self.value = value
        self.suit = suit

    def setValue(self, value):
        if value < 2 or value > self.ACE:
            raise ValueError("Card value out of range: " + str(value))
        self.value = value

    def setSuit(self, suit):
        if suit < self.CLUBS or suit > self.SPADES:
            raise ValueError("Suit value not valid:" + str(suit))
        self.suit = suit

    def getValue(self):
        return self.value  # look at me! I'm a Java programmer!

    def getSuit(self):
        return self.suit  # me too!

    def getValueAsString(self, value):
        if value == 2:
            return "Two"
        elif value == 3:
            return "Three"
        elif value == 4:
            return "Four"
        elif value == 5:
            return "Five"
        elif value == 6:
            return "Six"
        elif value == 7:
            return "Seven"
        elif value == 8:
            return "Eight"
        elif value == 9:
            return "Nine"
        elif value == 10:
            return "Ten"
        elif value == self.JACK:
            return "Jack"
        elif value == self.QUEEN:
            return "Queen"
        elif value == self.KING:
            return "King"
        elif value == self.ACE:
            return "Ace"
        else:
            return "Unknown Card"

    def getSuitAsString(self, suit):
        if suit == self.CLUBS:
            return "Clubs"
        elif suit == self.DIAMONDS:
            return "Diamonds"
        elif suit == self.HEARTS:
            return "Hearts"
        elif suit == self.SPADES:
            return "Spades"
        else:
            return "Unknown Suit"

    def toString(self):
        return (
            self.getValueAsString(self.value)
            + " of "
            + self.getSuitAsString(self.suit)
        )

    def __cmp__(self, other):
        if other is not None:
            return cmp(
                self.getValue() + self.getSuit(),
                other.getValue() + other.getSuit(),
            )
        return 1


# --------------------------------------------------------------------------


class player:
    def __init__(self, name):
        self.name = name
        self.cards = []
        self.pickedCards = []
        self.offered = (0, None)  # (int, Person)

    def getName(self):
        return self.name

    def setName(self, name):
        self.name = name

    def addToHand(self, c):
        self.cards.append(c)

    def removePickedCards(self):
        array = self.pickedCards
        self.pickedCards = []
        return array

    def getHand(self):
        return self.cards + self.pickedCards

    def getPicked(self):
        return self.pickedCards + []

    def pick(self, c):
        for i in self.cards:
            if c == i:
                self.pickedCards.append(i)
                self.cards.remove(i)
                return True
        return False

    def unpick(self, c):
        for i in self.pickedCards:
            if c == i:
                self.cards.append(i)
                self.pickedCards.remove(i)
            return True
        return False

    def offer(self, numcards, towhom):
        self.offered = (numcards, towhom)


# --------------------------------------------------------------------------


class EmptyDeckError(Exception):
    def __init__(self, value=0):
        self.value = value


# --------------------------------------------------------------------------


class cardbotFactory(protocol.ClientFactory):
    def __init__(self, channel='#cardgame', dealer='Iguana'):
        # protocol.ClientFactory.__init__(self) # No __init__ method!
        self.protocol = cardbot(dealer)
        self.mainchannel = channel

    def getUserInfo(self, user):
        x = user.split("!")
        z = x[1].split("@")
        return cardbotUser(x[0], z[0], z[1])

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()


# --------------------------------------------------------------------------

if __name__ == '__main__':
    config = ConfigParser()
    try:
        config.read(sys.argv[1])
    except:
        sys.exit('Missing config filename or bad config file')

    network = config.get('global', 'network')
    channel = config.get('global', 'channel')
    dealer = config.get('global', 'dealer')
    reactor.connectTCP(network, 6667, cardbotFactory(channel, dealer))
    reactor.run()
