// Run dotenv
require('dotenv').config();

// npm install --save discord.js dotenv
const Discord = require('discord.js');
const pynode = require('@fridgerator/pynode');

pynode.startInterpreter();
pynode.appendSysPath('../');
const cmdparser = pynode.import('cmdparser');
const python_builtins = pynode.import('builtins');

class DiscordUser {
    constructor(djsuser) {
        this.djsuser = djsuser;
        console.log("new NodeUser with djsuser " + this.djsuser);
        console.log("                  this = " + this);
    }
    get_id() {
        console.log("get_id() called; djsuser = " + this.djsuser);
        console.log("                 this = " + this);
        return this.djsuser.username + "#" + this.djsuser.discriminator;
    }
    toString() {
        return "DiscordUser{djsuser=" + this.djsuser + "}"
    }
}

function send_function(to, msg) {
    console.log("SjEND FUNCTION");
    args = Array.from(arguments).slice(2);
    console.log(args);
    pyargs = python_builtins.get('tuple').call(args)
    console.log(pyargs)
    //console.log("yeah I ran fine 4")
    //console.log(cmdparser.get('test').call(msg, pyargs))
    //console.log("yeah I ran fine 3")
    //message = python_builtins.get('str').get('__mod__').call("test %d %s", python_builtins.get('tuple').call([1, 'farts']));
    //console.log("yeah I ran fine 2")
    //message = python_builtins.get('str').get('__mod__').call(msg, python_builtins.get('tuple').call([1, 'farts']));
    //console.log("yeah I ran fine 1")
    message = python_builtins.get('str').get('__mod__').call(msg, python_builtins.get('tuple').call(pyargs));
    console.log("yeah I ran fine")
    console.log(message);
    if (to == "channel") {
        global.gamechannel.send(message);
    } else {
        /* to is a DiscordUser */
        to.djsuser.send(message);
    }
}

function get_names_function(callback) {
    users = [];
    console.log(client.users.cache);
    for ([key, user] of client.users.cache) {
        if (user instanceof Discord.User) {
            if ((!user.bot) && (user.presence.status == 'online')) {
                users.push(new DiscordUser(user));
            }
        }
    }
    callback.call(users);
}

const client = new Discord.Client();
const parser = cmdparser.get('Parser').call(
    send_function, get_names_function, process.env.SAVE_DIR)
console.log("Parser: " + parser);

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
    } else if (channel.name == process.env.GAME_CHANNEL) {
        origin = 'channel';
        global.gamechannel = channel;
    }

    console.log(`Will parse user ${user}, origin ${origin}, params ${params}`);

    if (msg.content === 'ping') {
        msg.reply('pong');
    } else {
        parser.get('parse').call(new DiscordUser(user), origin, params);
    }
});

client.login(process.env.DISCORD_TOKEN);
