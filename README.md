# TrainGame IRC Bot

A virtual play area for train-based card play.

The bot is controlled by players within an IRC channel and in private messages (PMs) to individual players.

### Installation and running

Optionally create and activate a new virtualenv with the following line in the shell:

```
virtualenv -p python3 venv
source venv/bin/activate
```

Install dependencies using pip:

```
pip3 install -r requirements.txt
```

Copy the example `config.ini` to another file (eg `local.ini`) and edit it for your settings (dealer is currently ignored):

```
[global]
network=irc.example.com
channel=#cardgame
nickname=BotNick
dealer=DealerNick
```

Finally, run the bot. It will connect to the given IRC network and join the given channel.

```
python3 ircbot.py local.ini
```

Each bot currently controls one and only one game (though you still have to start it with 'new' or 'load'; see below.)

You will also need a `default` savegame which is used to initialise new games. Create a directory called `state/default` and inside place two text files, `deck.txt` and `tickets.txt`. These contain the two main decks of cards, with one named card per line. Example:

`deck.txt`
```
RED
RED
RED
ORANGE
ORANGE
LOCOMOTIVE
```

`tickets.txt`
```
[EARTH<->MOON 100 pts]
[MARS<->VENUS 1138 pts]
[IO<->EUROPA 666 pts]
```

### Model

The game is played using various actions that moves cards between various _piles_.

The various piles and typical transfer commands are shown below.

```
+---------+        +---------------+
| DISCARD | <------+ Cards in PLAY |
+----+----+        +----+----------+
     ^                  ^         |
     | discard peek     | play    | unplay
     |                  |         v
+----+----+        +----+-----------------+
|  PEEK   |    +-> |  Each player's HAND  |
+----+----+   /    +----+-----------------+
     ^       /          ^
     | peek / take      | pick
     |     /            |
+----+----+        +----+------+
|  DECK   +------> |  BUFFER   |
+---------+        |  5 slots  |
                   +-----------+


+---------+        +-----------------------+
| TICKETS +------> | MYTICKETS             |
+---------+ take   | Each player's tickets |
            from   +----+------------------+
            tickets     |
                        | discard
+-------------------+   | from
| DISCARDED TICKETS | <-+ mytickets
+-------------------+
```

### Commands

#### In-channel

Commands are given in the form: `[Botname]: command`. The need for `[Botname]` can currently be changed in code.

* `new`: Start a new game using the "default" savestate. Deck etc will be shuffled.
* `hand`: Display the player's hand.
* `take <count> [from <pile>]`: Take a given number of cards from the given pile (default: `deck`) into the player's `hand`. As a special case, cards taken from `tickets` are moved into the player's `mytickets`.
* `pick <position> [from <buffer>]`: Pick a card at the given position in the buffer pile. Put cards into the player's `hand`. Buffer is replenished automatically.
* `play <position1> [<position2> ...]`: Put the cards at the given positions in the player's `hand` into `play`. This is announced in-channel.
* `unplay`: Takes the cards in `play` back into the player's `hand`.
* `discard [from] <pile> [<pos1> [<pos2> ...]]`: Discards the cards at the given positions from the given pile, or all cards if no positions are given. Pile defaults to `play`.
* `peek [<count>]`: Reveals the given number of cards (or 1 card) from the `deck`. Cards sit in the `peek` pile until discarded.
* `show [<pile>]`: Show a particular pile. Lists piles if no pile given.
* `save <name>`: Save the game state to the given name.
* `load <name>`: Load the game state from the given name.
* `debug`: Enable remote console. Instructions are printed to bot's stdout.


#### Private message to bot

Commands are given in the form `command`; ie prefixing with the Bot's name is not required.

* `hand`: as above.
* `play`: as above.
* `unplay`: as above.
* `show`: as above.

