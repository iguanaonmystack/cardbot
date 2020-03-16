import os
import re
import shutil
import random

class Card:
    def __init__(self, name):
        assert isinstance(name, str)
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'Card(%r)' % self.name


class PileEmptyError(Exception):
    '''Raised when trying to pop from an empty pile'''
    pass


class NotAPlayerError(ValueError):
    '''Raised when get_player finds no matching player.'''


class Pile(list):
    "Pile of cards"

    def __init__(self, cards=[], open_play=False, discard_to=None, auto_replenish_from=None):
        super().__init__(cards)
        self.open_play = open_play
        self.discard_to = discard_to
        self.auto_replenish_from = auto_replenish_from

    def append(self, obj):
        assert (obj is None) or isinstance(obj, Card)
        super().append(obj)

    def extend(self, obj):
        for o in obj:
            assert (o is None) or isinstance(o, Card)
        super().extend(obj)

    def pop(self, idx=-1):
        if len(self) == 0 and self.auto_replenish_from:
            print("shuffling and replenishing")
            random.shuffle(self.auto_replenish_from)
            self[:] = self.auto_replenish_from
            self.auto_replenish_from.clear()
        if len(self) == 0:
            raise PileEmptyError()
        return super().pop(idx)

    def load(self, l):
        '''l -- list of strings, each representing a card'''
        for item in l:
            assert isinstance(item, str)
            self.append(Card(item))

    def dump(self):
        '''Inverse of load -- returns a list of strings'''
        return [str(card) for card in self]

    def __str__(self):
        if not self.open_play:
            return '[%d cards in a pile]' % len(self)
        return ', '.join(
            '%d: %s' % (i, card) for i, card in enumerate(self.dump()))

    def __repr__(self):
        return 'Pile(%r)' % super().__repr__()

    def take_from(self, other, count=1):
        for i in range(count):
            self.append(other.pop())

    def discard(self):
        self.discard_to.extend(self)
        self[:] = []


class Buffer(Pile):
    def __init__(self, cards=[], open_play=False, discard_to=None, size=5):
        super().__init__(cards, open_play)
        self.size = size
        while len(self) < size:
            self.append(None)

    def fill_from(self, from_):
        for i in range(len(self)):
            if self[i] is None:
                card = from_.pop()
                self[i] = card

    def pop(self, idx=-1):
        if idx == -1:
            idx = len(self) - 1
            while self[idx] is None:
                idx -= 1
                if idx < 0:
                    raise IndexError('Buffer is empty')
        item = self[idx]
        self[idx] = None
        if item is None:
            raise IndexError('Buffer is empty at this position')
        return item


class Player:
    def __init__(self, name, game):
        self.name = name
        self.game = game
        self.game.players.append(self)
        self.hand = Pile(open_play=True)

    def take(self, count=1, from_=None, from_index=-1):
        if from_ is None:
            from_ = self.game.deck
        for i in range(count):
            card = from_.pop(from_index)
            self.hand.append(card)

    def play(self, *idxs):
        cards = [self.hand[i] for i in idxs]
        self.game.in_play.extend(cards)
        for i in reversed(sorted(idxs)):
            self.hand.pop(i)

    def __str__(self):
        return str(self.name)


class Game:
    def __init__(self):
        self.savedir = 'state'
        self.discard = Pile(open_play=True)
        self.deck = Pile(auto_replenish_from=self.discard)
        self.buffer = Buffer(open_play=True, size=5, discard_to=self.discard)
        self.peek = Pile(open_play=True, discard_to=self.discard)
        self.in_play = Pile(open_play=True, discard_to=self.discard)
        self.players = []

    def valid_gamename(self, gamename):
        # must be a valid, secure directory name
        return re.match(r'^[a-zA-Z0-9-_]+$', gamename)

    def load(self, gamename):
        if not self.valid_gamename(gamename):
            raise ValueError('Invalid game name: %r' % (gamename,))
        dirname = os.path.join(self.savedir, gamename)
        with open(os.path.join(dirname, 'deck.txt')) as f:
            cards = [line.strip() for line in f]
        # TODO - other piles
        self.deck.load(cards)

    def save(self, gamename):
        if not self.valid_gamename(gamename):
            raise ValueError('Invalid game name: %r' % (gamename,))
        dirname = os.path.join(self.savedir, gamename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        for pile, filename in (
                (self.discard, 'discard.txt'),
                (self.deck, 'deck.txt'),
                (self.buffer, 'buffer.txt'),
                (self.peek, 'peek.txt'),
                (self.in_play, 'in_play.txt')):
            self._save_pile(pile, dirname, filename)
        for player in self.players:
            self._save_pile(
                player.hand, dirname, 'player_%s_hand.txt' % player.name)
        
    def _save_pile(self, pile, dirname, filename):
        with open(os.path.join(dirname, filename), 'w') as f:
            for card in pile:
                print(str(card), file=f)

    def get_player(self, name):
        assert isinstance(name, str)
        for player in self.players:
            if player.name == name:
                return player
        raise NotAPlayerError()


def run_test_game():
    import sys
    def info(type, value, tb):
        import traceback, pdb
        traceback.print_exception(type, value, tb)
        print()
        # start the debugger in post-mortem mode
        pdb.pm()
    sys.excepthook = info

    game = Game()
    game.load('default')
    random.shuffle(game.deck)
    iguana = Player('Iguana', game)
    tiger = Player('Tiger', game)
    assert iguana.name == 'Iguana'
    assert tiger.name == 'Tiger'
    deck_size = len(game.deck)
    iguana.take(4)
    tiger.take(4)
    assert len(game.deck) == deck_size - 8
    assert len(iguana.hand) == 4
    assert len(tiger.hand) == 4
    game.buffer.fill_from(game.deck)
    print(game.buffer)
    assert len(game.buffer) == 5
    assert len(game.deck) == deck_size - 8 - 5
    card_1 = game.buffer[0]
    card_4 = game.buffer[3]
    iguana.take(1, game.buffer, 0)
    game.buffer.fill_from(game.deck)
    iguana.take(1, game.buffer, 3)
    game.buffer.fill_from(game.deck)
    assert len(game.deck) == deck_size - 8 - 5 - 2
    assert iguana.hand[-2] is card_1
    assert iguana.hand[-1] is card_4
    assert len(iguana.hand) == 6
    tiger.play(0, 3, 2)
    assert len(tiger.hand) == 1
    assert len(game.in_play) == 3
    game.peek.take_from(game.deck, 3)
    assert len(game.peek) == 3
    assert len(game.deck) == deck_size - 8 - 5 - 2 - 3
    game.peek.discard()
    game.in_play.discard()
    assert len(game.deck) == deck_size - 8 - 5 - 2 - 3
    assert len(game.peek) == 0
    assert len(game.in_play) == 0
    assert len(game.discard) == 6
    if os.path.exists('test-save'):
        shutil.rmtree('test-save')
    game.save('test-save')

    iguana.take(10)
    print(iguana.hand)


if __name__ == '__main__':
    run_test_game()

