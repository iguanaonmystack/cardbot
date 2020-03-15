#!/usr/bin/env python3

import sys
import random
from configparser import ConfigParser

from twisted.internet import reactor, protocol

import game
import namesircclient

class CardbotUser:
    def __init__(self, nick, ident, realname):
        self.nick = nick
        self.ident = ident
        self.realname = realname
        self.player = None

    def __str__(self):
        return self.nick

    def __eq__(self, other):
        # TODO - this should just return if an IRC user is the
        # same user as an earlier seen version. Is just the ident enough?
        return (self.nick == other.nick
                and self.ident == other.ident
                and self.realname == other.realname)


class Cardbot(namesircclient.NamesIRCClient):

    def __init__(self, dealer, mainchannel):
        super().__init__()
        self.nickname = "TrainGame"
        self.realname = "this code works??"
        self.dealer = dealer
        self.mainchannel = mainchannel
        self.players = []
        self.helpURL = "http://example.com/projects/cardbot.shtml"
        self.game = None
        self.users = []

    def signedOn(self):
        self.mode(self.nickname, False, "x")
        self.join(self.mainchannel)

    def userJoined(self, user, channel):
        print("join: %s to %s" % (user, channel))

    def userLeft(self, user, channel):
        print("part: %s from %s" % (user, channel))

    def userRename(self, oldname, newname):
        print("nickchange: %s to %s" % (oldname, newname))
        player = self.getPlayer(oldname)
        if player is not None:
            player.setName(newname)

    def kickedFrom(self, channel, kicker, msg):
        print("%s kicked me from %s (%s)" % (kicker, channel, msg))

    def action(self, user, channel, msg):
        user = self.factory.getUserInfo(user)
        print("* %s %s" % (user.nick, msg))

    def noticed(self, user, channel, msg):
        pass

    def getUser(self, ircuser):
        username, ident_realname = ircuser.split('!', 1)
        ident, realname = ident_realname.split('@', 1)
        user = CardbotUser(username, ident, realname)
        for existing_user in self.users:
            if user == existing_user:
                return existing_user
        self.users.append(user)
        return user

    def privmsg(self, user, channel, msg):
        user = self.getUser(user)
        print("<%s:%s> %s" % (user.nick, channel, msg))

        mlc = msg.lower()

        print(channel)
        if self.nickname == channel:
            # if channel is self.nickname, it's a PM.
            params = mlc.split()
            command = params[0]
            print(params, command)

            command_function = {
                'hand': self.display_hand,
                'show': self.show_pile,
            }.get(command, self.unknown_command)
            command_function(params, user, user.nick)

        else:
            # otherwise, it's in a channel.
            params = mlc.split()
            if params[0] != self.nickname.lower() \
                    and params[0][:-1] != self.nickname.lower():
                # not addressed to me
                return
            try:
                params = params[1:]
            except IndexError:
                params = []
            try:
                command = params[0]
            except IndexError:
                command = ''

            command_function = {
                'new': self.new_game,
                'hand': self.display_hand,
                'take': self.take_cards,
                'pick': self.pick_card,
                'show': self.show_pile,
                'debug': self.enable_debug,
            }.get(command, self.unknown_command)
            command_function(params, user, channel)

    def unknown_command(self, params, sender, destination):
        print(params, sender, destination)
        self.msg(destination, "Unknown command from %s: %r" % (sender, params))

    def enable_debug(self, params, sender, destination):
        print("Starting debugger; connect with: "
              "python3 -c 'import epdb; epdb.connect()'")
        import epdb
        epdb.serve()

    def new_game(self, params, sender, destination):
        self.game = game.Game()
        self.game.load('default')
        random.shuffle(self.game.deck)
        self.game.buffer.fill_from(self.game.deck)
        self.names(self.mainchannel).addCallback(self._got_names_for_new_game(destination))

    def _got_names_for_new_game(self, destination):
        def _internal(nicklist):
            for nick in nicklist:
                if not nick or nick.lower() == self.nickname.lower():
                    continue
                while nick.startswith("@"):
                    nick = nick[1:]
                game.Player(nick, self.game)
            self.msg(destination,
                     "New game with %s" % (
                         ', '.join(str(p) for p in self.game.players)))
        return _internal

    def display_hand(self, params, sender, destination):
        player = self.game.get_player(sender.nick)
        hand = player.hand
        self.msg(destination, "%s hand: %s" % (player, hand))

    def show_pile(self, params, sender, destination):
        player = self.game.get_player(sender.nick)
        piles = {'deck': self.game.deck,
                 'buffer': self.game.buffer}
        pile = piles[params[1]]
        self.msg(destination, '%s: %s' % (params[1], pile))

    def pick_card(self, params, sender, destination):
        '''"pick [position] [from buffer]"'''
        piles = {'buffer': self.game.buffer}
        pile = 'buffer'
        try:
            from_pos = params.index('from')
        except ValueError:
            from_pos = None
        if not from_pos:
            # command must be 'pick [position]'
            if len(params) == 2:
                position = int(params[1])
            else:
                position = 1
        else:
            # command is 'pick [count] from [pile]'
            assert len(params) == 4
            position = int(params[1])
            pile = piles[params[3]]
        player = self.game.get_player(sender.nick)
        player.take(1, piles[pile], position)
        self.msg(destination, "%s picked a card from %s" % (player, pile))
        self.game.buffer.fill_from(self.game.deck)
        self.msg(destination, "Replenished %s: %s" % (pile, self.game.buffer))
        self.msg(player, "New hand: %s" % (player.hand,))

    def take_cards(self, params, sender, destination):
        '''"take [count] [from deck]"'''
        piles = {'deck': self.game.deck}
        pile = 'deck'
        try:
            from_pos = params.index('from')
        except ValueError:
            from_pos = None
        if not from_pos:
            # command must be 'take [count]'
            if len(params) == 2:
                count = int(params[1])
            else:
                count = 1
        else:
            # command is 'take [count] from [pile]'
            assert len(params) == 4
            count = int(params[1])
            pile = piles[params[3]]
        player = self.game.get_player(sender.nick)
        player.take(count, piles[pile], -1)
        self.msg(destination, "%s took %s from %s" % (player, count, pile))
        self.msg(player, "New hand: %s" % (player.hand,))


class CardbotFactory(protocol.ClientFactory):
    def __init__(self, channel='#cardgame', dealer='Iguana'):
        self.main_channel = channel
        self.original_dealer = dealer

    def buildProtocol(self, addr):
        protocol = Cardbot(self.original_dealer, self.main_channel)
        protocol.factory = self
        return protocol

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()


if __name__ == '__main__':
    config = ConfigParser()
    try:
        config.read(sys.argv[1])
    except:
        sys.exit('Missing config filename or bad config file')

    network = config.get('global', 'network')
    channel = config.get('global', 'channel')
    dealer = config.get('global', 'dealer')
    reactor.connectTCP(network, 6667, CardbotFactory(channel, dealer))
    reactor.run()
