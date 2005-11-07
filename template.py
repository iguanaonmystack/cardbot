from twisted.protocols.irc import IRCClient
from twisted.internet import reactor, protocol

class cardbotUser:
	def __init__(self, username, ident, realname):
		self.username = username
		self.ident = ident
		self.realname = realname

	def name(self):
		return self.username

class cardbot(IRCClient):
	def __init__(self):
		self.nickname = "CardPack"
		self.realname = "realname"

	def signedOn(self):
		self.mode(self.nickname, False, "x")
		self.join("#cardgame")

	def userJoined(self, user, channel):
		print "join: %s to %s" % (user, channel)
	
	def userLeft(self, user, channel):
		print "part: %s from %s" % (user, channel)
	
	def userRename(self, oldname, newname):
		print "nickchange: %s to %s" % (oldname, newname)
	
	def kickedFrom(self, channel, kicker, msg):
		print "%s kicked me from %s (%s)" % (kicker, channel, msg)

	def privmsg(self, user, channel, msg):
		user = self.factory.getUserInfo(user)
		print "<%s|%s> %s" % (user.name(), channel, msg)
		if msg.startswith(self.nickname):
			self.me(channel, "waves")
	
	def action(self, user, channel, msg):
		user = self.factory.getUserInfo(user)
		print "* %s %s" % (user.name(), msg)

	def noticed(self, user, channel, msg):
		pass

class cardbotFactory(protocol.ClientFactory):
	protocol = cardbot

	def getUserInfo(self, user):
		x = user.split("!")
		z = x[1].split("@")
		return cardbotUser(x[0], z[0], z[1])

	def clientConnectionLost(self, connector, reason):
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		reactor.stop()

class Card:
	JACK = 11
	QUEEN = 12
	KING = 13
	ACE = 14  # arbitrary choice


if __name__ == '__main__':
	reactor.connectTCP("coruscant.slashnet.org", 6667, cardbotFactory())
	reactor.run()
