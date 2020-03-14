# CardPack IRC Bot

The CardPack IRC Bot is a virtual deck of cards that is controlled by a user allocated to be the dealer. This is configured in config.ini.  

The Bot communicates to players via Private Messages, and reads of status and gameplay things in the channel.

### Commands

#### In-channel

*   Commands are given in the form: "CardPack: command variables"
*   `dealer _nick_`: Change the dealer to nick
*   `reveal`: Reveal your hand to the channel
*   `showhand`: Does the same as reveal
*   `showpicked`: Show the channel the cards that you have picked to give back to the deck
*   `giveback`: Give back the cards that you have picked to the deck
*   `givehandto _nick_`: Give your hand to someone else. This magically transforms that person into a player. You can only pass your hand to a non-player.
*   `offer _player numcards_`: Let another player take a number of your cards. A player can only offer cards to one person at a time.
*   `unoffer`: Withdraw your offer of cards.
*   `help`: Gives the URL of this page

#### In-channel (dealer-only)

*   Command are given in the form: "CardPack: command variables"
*   `reset`: Reset the pack and clear the current players.
*   `addplayer _nick_`: Add a player to the game. nick indicates their IRC nickname. A person cannot play before being added as a player. A player is notified via PM that they have been added.
*   `addplayers _nick1 nick2 nick3 ..._`: Add several players at once.
*   `remplayer`: Removes a player, returning their cards to the deck.
*   `dealto _nick number_`: deal one or several cards to a player. nick is the player's nickname, number is the number of cards to deal to them. If omited, number defaults to 1.
*   `deal _number_`: deal one or several cards to all the current players. Again, number is optional
*   `play21`: shortcut to set up a game of 21\. Each player receives two cards.

#### Private Messages

*   Commands are given in the form: "command variables"
*   `showhand`: Shows your current hand. Same as in-channel "reveal" but obviously this way nobody can see which cards you have.
*   `showpicked`: Shows which cards you have picked to give back to the deck. Same as in-channel "showpicked" but obviously this way nobody can see which cards you've picked.
*   `pick _card_`: Possibly the most complicated command for the bot. Picks a card that you can later return to the deck using the in-channel "giveback" command. The card variable is in the form [value][suitletter]. For example, 2H is the 2 of Hearts. 10H is the 10 of Hearts, AS is the Ace of Spades, JC is the Jack of Clubs, QD is the Queen of Diamonds, and KD is the King of Diamonds.
*   `unpick _card_`: Unpick a previously picked card. Same format as `pick`

#### TODO

*   `takefrom _player card1 card2 ..._`: Pick cards from another player, following their permission given in the form of `offer`. The engine should randomise the order of the giver's cards just before they "pick a number" to avoid players cheating behind the scenes. card1, card2, etc should be a number indicating a card in the giver's hand. For example, if the giver holds five cards, the receiver can pick 1, 2, 3, 4, or 5\. The reciever should be allowed to pick less cards than offered, but if he does so, the offer to take the rest of the cards expires. Channel only.
*   `request _player numcards_`: Request that a player gives you a number of cards. Channel only
*   `giveto _player cardID1 cardID2 ..._`: Give a player that has requested cards from you some cards. cardIDx works the same as the pick syntax. This should be PM only to avoid giving away what's on the card to other players, but a confirmation of the transaction should be given in-channel.
*   Shortcut aliases for all the commands.
