#!/usr/bin/env python3

import sys
import random
from configparser import ConfigParser

from twisted.internet import reactor, protocol

import game
import namesircclient

class IRCUser:
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
        self.require_mention = True

    def signedOn(self):
        self.mode(self.nickname, False, "x")
        self.join(self.mainchannel)

    def userJoined(self, user, channel):
        print("join: %s to %s" % (user, channel))

    def userLeft(self, user, channel):
        print("part: %s from %s" % (user, channel))

    def userRename(self, oldname, newname):
        print("nickchange: %s to %s" % (oldname, newname))
        try:
            player = self.game.get_player(oldname)
        except game.NotAPlayerError:
            return
        player.name = newname

    def kickedFrom(self, channel, kicker, msg):
        print("%s kicked me from %s (%s)" % (kicker, channel, msg))

    def action(self, user, channel, msg):
        user = self.getUser(user)
        print("* %s %s" % (user.nick, msg))

    def noticed(self, user, channel, msg):
        pass

    def getUser(self, ircuser):
        username, ident_realname = ircuser.split('!', 1)
        ident, realname = ident_realname.split('@', 1)
        user = IRCUser(username, ident, realname)
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
                'play': self.play_cards,
                'unplay': self.unplay,
                'show': self.show_pile,
            }.get(command, self.unknown_command)
            command_function(params, user, user.nick)

        else:
            # otherwise, it's in a channel.
            params = mlc.split()
            if params[0] != self.nickname.lower() \
                    and params[0][:-1] != self.nickname.lower():
                # not addressed to me
                if self.require_mention:
                    return
            else:
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
                'play': self.play_cards,
                'unplay': self.unplay,
                'discard': self.discard,
                'peek': self.peek,
                'show': self.show_pile,
                'save': self.save_game,
                'load': self.load_game,
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
        random.shuffle(self.game.tickets)
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

    def load_game(self, params, sender, destination):
        self.game = game.Game()
        self.game.load(params[1])

    def save_game(self, params, sender, destination):
        self.game.save(params[1])

    def display_hand(self, params, sender, destination):
        player = self.game.get_player(sender.nick)
        hand = player.hand
        self.msg(destination, "%s hand: %s" % (player, hand))

    def show_pile(self, params, sender, destination):
        player = self.game.get_player(sender.nick)
        piles = {'deck': self.game.deck,
                 'play': self.game.in_play,
                 'peek': self.game.peek,
                 'discard': self.game.discard,
                 'tickets': self.game.tickets,
                 'hand': player.hand,
                 'mytickets': player.tickets,
                 'buffer': self.game.buffer}
        try:
            if len(params) > 1:
                pile = piles[params[1]]
            else:
                raise ValueError()
        except (ValueError, KeyError):
            self.msg(destination, 'Available piles: %s' % (
                ', '.join(piles.keys())))
        self.msg(destination, '%s: %s' % (params[1].title(), pile))

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
        player = self.game.get_player(sender.nick)
        piles = {
            'deck': self.game.deck,
            'tickets': self.game.tickets
        }
        pilename = 'deck'
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
            pilename = params[3]

        if pilename not in piles:
            self.msg(destination, "Available piles: %s" % (
                ', '.join(piles.keys())))
            return
        pile = piles[pilename]
        if pile == self.game.tickets:
            player.ticket(count)
            hand_to_show = player.tickets
        else:
            player.take(count, pile, -1)
            hand_to_show = player.hand
        self.msg(self.mainchannel,
                 "%s took %s from %s" % (player, count, pile))
        self.msg(player, "New hand: %s" % (hand_to_show,))

    def play_cards(self, params, sender, destination):
        '''"play [pos] [[pos] ...]"'''
        player = self.game.get_player(sender.nick)
        positions = [int(pos) for pos in params[1:]]
        player.play(*positions)
        self.msg(self.mainchannel, "In play: %s" % (self.game.in_play))
        self.msg(self.mainchannel, "(unplay or discard to remove from play)")
        self.msg(player, "New hand: %s" % (player.hand,))

    def unplay(self, params, sender, destination):
        player = self.game.get_player(sender.nick)
        player.take(len(self.game.in_play), self.game.in_play)
        self.msg(self.mainchannel, "%s takes back cards in play" % (player,))
        self.msg(player, "New hand: %s" % (player.hand,))

    def discard(self, params, sender, destination):
        '''"discard [from] [pilename] [posn ...]" -- discard cards in a pile'''
        player = self.game.get_player(sender.nick)
        piles = {
            'play': self.game.in_play,
            'peek': self.game.peek,
            'mytickets': player.tickets}
        if len(params) > 1:
            if params[1] == 'from':
                params.pop(1)
            if len(params) > 1:
                pilename = params[1]
        else:
            pilename = 'play'
        if len(params) > 2:
            positions = [int(posn) for posn in params[2:]]
        if pilename not in piles:
            self.msg(destination, 'Available piles: %s' % (
                ', '.join(piles.keys())))
        pile = piles[pilename]
        if pile is player.tickets:
            count = len(positions)
            positions.sort(reverse=True)
            for position in positions:
                card = pile.pop(position)
                self.game.old_tickets.append(card)
        else:
            count = pile.discard()
        self.msg(self.mainchannel, "Discarded %s cards in %s" % (
            count, pilename))

    def peek(self, params, sender, destination):
        '''"peek [count]" -- draw cards from deck into peek pile'''
        player = self.game.get_player(sender.nick)
        count = 1
        if len(params) > 1:
            count = int(params[1])
        self.game.peek.take_from(self.game.deck, count)
        self.msg(self.mainchannel, "Peek: %s" % (self.game.peek,))


class CardbotFactory(protocol.ClientFactory):
    def __init__(self, channel='#cardgame', dealer='Iguana'):
        self.mainchannel = channel
        self.original_dealer = dealer

    def buildProtocol(self, addr):
        protocol = Cardbot(self.original_dealer, self.mainchannel)
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
