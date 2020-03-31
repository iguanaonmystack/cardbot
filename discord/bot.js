// Run dotenv
require('dotenv').config();

// npm install --save discord.js dotenv
const Discord = require('discord.js');
const client = new Discord.Client();

client.on('ready', () => {
    console.log(`Logged in as ${client.user.tag}!`);
});

client.on('message', msg => {
    if (msg.author.bot) {
        console.log(`Ignoring message from bot ${msg.author.username}`);
        return;
    }
    var user = msg.author;
    var channel = msg.channel;
    var mlc = msg.content.toLowerCase();
    var params = mlc.split(' ');

    var origin = 'direct';
    var reply_fn;
    if (channel instanceof Discord.DMChannel) {
        origin = 'direct';
        reply_fn = function(text) { msg.reply(text); };
    } else if (channel.name == process.env.GAME_CHANNEL) {
        origin = 'channel';
        reply_fn = function(text) { channel.send(text); };
    }

    reply_fn(`Will parse user ${user}, origin ${origin}, params ${params}`);

    if (msg.content === 'ping') {
        msg.reply('pong');
    }
});

client.login(process.env.DISCORD_TOKEN);
