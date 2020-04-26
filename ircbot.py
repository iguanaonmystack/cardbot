#!/usr/bin/env python3

import sys
import random
from configparser import ConfigParser

from twisted.internet import reactor, protocol

import game
import cmdparser
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

    def get_id(self):
        return self.nick.lower()


class Cardbot(namesircclient.NamesIRCClient):

    def __init__(self, nickname, dealer, mainchannel, savedir):
        super().__init__()
        self.nickname = nickname
        self.realname = "this code works??"
        self.dealer = dealer
        self.mainchannel = mainchannel
        self.players = []
        self.helpURL = "http://example.com/projects/cardbot.shtml"
        self.parser = cmdparser.Parser(self.send, self.get_users, savedir)
        self.users = []
        self.require_mention = False

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
            if self.parser is not None and self.parser.game is not None:
                player = self.parser.game.get_player(oldname)
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
        params = mlc.split()

        if channel == self.nickname:
            # If channel is self.nickname, it's a PM.
            origin = 'direct'
        else:
            # If in a channel, check if the bot was mentioned.
            origin = 'channel'
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
        self.parser.parse(user, origin, params)

    def send(self, to, msg, *percent_args):
        if isinstance(to, IRCUser):
            to = to.nick
        elif to == 'channel':
            to = self.mainchannel
        else:
            raise ValueError("Unknown destination for send(): %r" % (to,))
        self.msg(to, msg % percent_args)

    def get_users(self, callback):
        '''Called by cmdparser.Parser when it wants users for a new game.'''
        self.names(self.mainchannel).addCallback(self._got_users(callback))

    def _got_users(self, callback):
        def _internal(nicklist):
            users = []
            for nick in nicklist:
                if not nick or nick.lower() == self.nickname.lower():
                    continue
                while nick.startswith("@"):
                    nick = nick[1:]
                users.append(IRCUser(nick, None, None))
            callback(users)
        return _internal


class CardbotFactory(protocol.ClientFactory):
    def __init__(self, nickname, channel='#cardgame', dealer='Iguana', savedir='./state'):
        self.nick = nickname
        self.mainchannel = channel
        self.original_dealer = dealer
        self.savedir = savedir

    def buildProtocol(self, addr):
        protocol = Cardbot(self.nick, self.original_dealer, self.mainchannel, self.savedir)
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
    nick = config.get('global', 'nickname')
    dealer = config.get('global', 'dealer')
    savedir = config.get('global', 'savedir')
    reactor.connectTCP(
        network, 6667,
        CardbotFactory(nick, channel, dealer, savedir))
    reactor.run()
