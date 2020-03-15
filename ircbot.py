#!/usr/bin/env python3

import sys
import random
from configparser import ConfigParser

from twisted.words.protocols.irc import IRCClient
from twisted.internet import reactor, protocol

import game


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


class Cardbot(IRCClient):

    def __init__(self, dealer, mainchannel):
        self.nickname = "TrainGame"
        self.realname = "this code works??"
        self.dealer = dealer
        self.mainchannel = mainchannel
        self.players = []
        self.helpURL = "http://example.com/projects/cardbot.shtml"
        self.game = game.Game()
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
                'show': self.display_hand,
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
                'reset': self.reset_game,
            }.get(command, self.unknown_command)
            command_function(params, user, channel)

    def unknown_command(self, params, sender, destination):
        print (params, sender, destination)
        self.msg(destination, "Unknown command from %s: %r" % (sender, params))

    def display_hand(self, params, sender, destination):
        self.msg(destination, "Display hand")

    def reset_game(self, params, sender, destination):
        self.msg(destination, "resetting")

    def console(self, params, sender, destination):
        pass # TODO - fork a console


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
