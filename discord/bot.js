// https://medium.com/davao-js/2019-tutorial-creating-your-first-simple-discord-bot-47fc836a170b

// Run dotenv
require('dotenv').config();

const Discord = require('discord.js');
const client = new Discord.Client();

client.on('ready', () => {
    console.log(`Logged in as ${client.user.tag}!`);
});

client.on('message', msg => {
    if (msg.content === 'ping') {
        msg.reply('pong');
    }
});

client.login(process.env.DISCORD_TOKEN);
