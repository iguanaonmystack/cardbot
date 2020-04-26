import random

import game

def test(s, args):
    assert isinstance(args, tuple)
    print('test function: s='+repr(s)+"; args="+repr( args))
    print(s % args)
    print(str.__mod__(s, args))
    for arg in args:
        print(repr(arg))

def is_tuple(o):
    print('checking is tuple ' + repr(o))
    return isinstance(o, tuple)

class Parser:
    def __init__(self, send_function, get_names_function, savedir):
        self.send = send_function
        self.get_names = get_names_function
        self.game = None
        self.savedir = savedir

    def parse(self, sender, origin, params):
        '''Parse a game command.

        sender -- an opaque object denoting the sender of this
                  command. It must have a 'get_id' function
                  for Game to interact with it.
        origin -- either 'channel' or 'direct' denoting where the
                  command was sent from.
        params -- a list of tokens constituting the command and
                  its params.

        Returns nothing but often calls the send_function provided to __init__
        to provide feedback or the results of the command.
        '''
        assert origin in ('channel', 'direct')

        if origin == 'direct':
            command = params[0]
            print(params, command)

            command_function = {
                'hand': self.display_hand,
                'play': self.play_cards,
                'unplay': self.unplay,
                'show': self.show_pile,
                'beep': self.beep,
            }.get(command, self.unknown_command)
            command_function(params, sender, sender)

        else:
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
                'beep': self.beep,
            }.get(command, self.unknown_command)
            command_function(params, sender, 'channel')

    def unknown_command(self, params, sender, destination):
        print(params, sender, destination)
        self.send(destination, "Unknown command from %s: %r" % (sender, params))

    def enable_debug(self, params, sender, destination):
        print("Starting debugger; connect with: "
              "python3 -c 'import epdb; epdb.connect()'")
        import epdb
        epdb.serve()

    def new_game(self, params, sender, destination):
        self.game = game.Game(savedir=self.savedir)
        self.game.load('default')
        random.shuffle(self.game.deck)
        random.shuffle(self.game.tickets)
        self.game.buffer.fill_from(self.game.deck)
        self.get_names(self._got_names_for_new_game)

    def _got_names_for_new_game(self, remote_users):
        for user in remote_users:
            game.Player(user.get_id(), self.game)
        self.send('channel',
                  "New game with %d players: %s",
                  len(self.game.players),
                  ', '.join(str(p) for p in self.game.players))

    def load_game(self, params, sender, destination):
        self.game = game.Game()
        self.game.load(params[1])

    def save_game(self, params, sender, destination):
        self.game.save(params[1])

    def display_hand(self, params, sender, destination):
        player = self.game.get_player(sender)
        hand = player.hand
        self.send(destination, "%s hand: %s" % (player, hand))

    def show_pile(self, params, sender, destination):
        player = self.game.get_player(sender)
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
            self.send(destination, 'Available piles: %s' % (
                ', '.join(piles.keys())))
        else:
            self.send(destination, '%s: %s' % (params[1].title(), pile))

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
        player = self.game.get_player(sender)
        player.take(1, piles[pile], position)
        self.send(destination, "%s picked a card from %s" % (player, pile))
        self.game.buffer.fill_from(self.game.deck)
        self.send(destination, "Replenished %s: %s" % (pile, self.game.buffer))
        self.send(sender, "New hand: %s" % (player.hand,))

    def take_cards(self, params, sender, destination):
        '''"take [count] [from deck]"'''
        player = self.game.get_player(sender)
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
            self.send(destination, "Available piles: %s" % (
                ', '.join(piles.keys())))
            return
        pile = piles[pilename]
        if pile == self.game.tickets:
            player.ticket(count)
            hand_to_show = player.tickets
        else:
            player.take(count, pile, -1)
            hand_to_show = player.hand
        self.send('channel',
                 "%s took %s from %s" % (player, count, pile))
        self.send(sender, "New hand: %s" % (hand_to_show,))

    def play_cards(self, params, sender, destination):
        '''"play [pos] [[pos] ...]"'''
        player = self.game.get_player(sender)
        positions = [int(pos) for pos in params[1:]]
        player.play(*positions)
        self.send('channel', "In play: %s" % (self.game.in_play))
        self.send('channel', "(unplay or discard to remove from play)")
        self.send(sender, "New hand: %s" % (player.hand,))

    def unplay(self, params, sender, destination):
        player = self.game.get_player(sender)
        player.take(len(self.game.in_play), self.game.in_play)
        self.send('channel', "%s takes back cards in play" % (player,))
        self.send(sender, "New hand: %s" % (player.hand,))

    def discard(self, params, sender, destination):
        '''"discard [from] [pilename] [posn ...]" -- discard cards in a pile'''
        player = self.game.get_player(sender)
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
            self.send(destination, 'Available piles: %s' % (
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
        self.send('channel', "Discarded %s cards in %s" % (
            count, pilename))

    def peek(self, params, sender, destination):
        '''"peek [count]" -- draw cards from deck into peek pile'''
        player = self.game.get_player(sender)
        count = 1
        if len(params) > 1:
            count = int(params[1])
        self.game.peek.take_from(self.game.deck, count)
        self.send('channel', "Peek: %s" % (self.game.peek,))

    def beep(self, params, sender, destination):
        '''"beep" -- boop'''
        print("beeping: %r, %r, %r", params, sender, destination)
        self.send(destination, "boop")

