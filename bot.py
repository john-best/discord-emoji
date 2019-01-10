import discord
from discord.ext import commands
import requests
import re

import config

bot = commands.Bot(command_prefix='&')
bot.remove_command('help')

emoji_regex = "^<:(?P<name>[A-zA-Z0-9]*):(?P<id>[0-9]*)>$"
emoji_regex2 = "^:(?P<name>[A-zA-Z0-9]*):$"

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='{}emoji_help for Emoji Abuse'.format(bot.command_prefix)))
    pass

@bot.command(name="help")
async def handle_help(ctx):
    # TODO
    description = "`emoji twitch/ffz/bttv channelname emotename [customname]`\n `emoji url emotename`\n `emoji_delete emotename`\n `help`"
    embed = discord.Embed(description=description, color=0x5bc0de)
    embed.set_author(name="Emoji Discord Bot", url="https://github.com/john-best/discord-emoji")
    await ctx.message.channel.send(embed=embed)


# emoji [url/twitch/ffz] [username/url] [twitch/ffz emote if not url]
# bot AND caller needs to have manage emojis permission
@bot.command(name="emoji")
@commands.has_permissions(manage_emojis=True)
@commands.bot_has_permissions(manage_emojis=True)
async def handle_emoji(ctx):
    # two options:
    # emoji url actual_url emote_name
    # emoji twitch/ffz/bttv username emote_name [optional: custom_emote_name]

    await ctx.message.channel.trigger_typing()
    if len(ctx.message.content.split()) - 1 < 3:
        await ctx.message.channel.send("Error: Expected at least 3 params, found {}.".format(len(ctx.message.content.split()) - 1))
        return

    params = ctx.message.content.split()[1:]

    # url actual_url emote_name
    if params[0] == 'url':
        name = params[2]
        url = params[1]

        image = requests.get(url).content
        await handle_create_emoji(ctx, image, name)
        return
    
    # twitch username emote_name
    elif params[0] == 'twitch':
        url = "https://api.twitch.tv/api/channels/{}/product".format(params[1])
        name = params[2]

        # TODO: need to check response when channel doesn't exist
        emoticons = requests.request('GET', url=url, headers={"Client-ID": config.twitch_client_id}).json()["emoticons"]
        
        # in situations where the user can type the emoji
        # the emoji is replaced with <:name:id>
        
        match = re.match(emoji_regex, name)
        if match is not None:
            name = match.group("name")
          
        for emoticon in emoticons:
            if emoticon["regex"] == name:
                url = emoticon["url"]
                image = requests.get(url).content

                # custom name
                if len(params) == 4:
                    name = params[3]
                await handle_create_emoji(ctx, image, name)
                return
              
        await ctx.message.channel.send("Error: twitch emote not found!")
        return

    # ffz username emote_name
    elif params[0] == 'ffz':
        name = params[2]

        # in situations where the user can type the emoji
        # the emoji is replaced with <:name:id>
        match = re.match(emoji_regex, name)
        if match is not None:
            name = match.group("name")


        # search using channel name AND the search parameter
        url = "https://api.frankerfacez.com/v1/emoticons?q={}%20{}".format(params[1], name)
        emoticons = requests.get(url).json()["emoticons"]

        if len(emoticons) == 0:
            await ctx.message.channel.send("Error: unable to find FFZ emote with given channel name and emote name")
            return
        
        emoticon = emoticons[0]

        # when would we use the urls not located at the first location?
        image_url = emoticon["urls"]["1"]
        image = requests.get("https:{}".format(image_url)).content

        # custom name
        if len(params) == 4:
            name = params[3]
        await handle_create_emoji(ctx, image, name)

        # TODO: what happens when there are more than 1 result?
        # although given the channel name and emote name, only one should show up
        # this is probably low priority. maybe someday we can search on ffz using this bot!

        return

    # bttv
    elif params[0] == 'bttv':
        url = "https://api.betterttv.net/2/channels/{}".format(params[1])
        name = params[2]
        res = requests.get(url).json()

        if res["status"] == "404":
            await ctx.message.channel.send("Error: unable to find BetterTTV channel")
            return
        
        emotes = res["emotes"]


        # in situations where the user can type the emoji
        # the emoji is replaced with <:name:id>
        match = re.match(emoji_regex, name)
        if match is not None:
            name = match.group("name")

        emote_id = None

        for emote in emotes:
            if emote["code"] == name:
                emote_id = emote["id"]
                break

        if emote_id is None:
            await ctx.message.channel.send("Error: unable to find BetterTTV emote with given channel name and emote name")
        
        emote_url = "https://cdn.betterttv.net/emote/{}/1x".format(emote_id)
        image = requests.get(emote_url).content

        # custom name
        if len(params) == 4:
            name = params[3]
        await handle_create_emoji(ctx, image, name)

    else:
        await ctx.message.channel.send("Error: Invalid params. Check {}help for more information.".format(ctx.prefix))
        return

@bot.command(name="emoji_delete")
@commands.has_permissions(manage_emojis=True)
@commands.bot_has_permissions(manage_emojis=True)
async def handle_delete_emoji(ctx):
    await ctx.message.channel.trigger_typing()
    if len(ctx.message.content.split()) - 1 != 1:
        await ctx.message.channel.send("Error: Expected exactly 1 param, found {}.".format(len(ctx.message.content.split()) - 1))
        return

    name = ctx.message.content.split()[1]

    # if we want to delete an emoji it's most likely (100%??) going to pass through these conversions
    match = re.match(emoji_regex, name)
    if match is not None:
        name = match.group("name")
    
    match = re.match(emoji_regex2, name)
    if match is not None:
        name = match.group("name")

    for emoji in ctx.message.guild.emojis:
        if emoji.name == name:
            await emoji.delete()
            await ctx.message.channel.send("`:{}:` deleted.".format(name))
            return
    
    await ctx.message.channel.send("Error: could not find `:{}:`.".format(name))
# basic error handling to send to channel for easier debugging
@handle_emoji.error
async def handle_emoji_error(ctx, error):
    await ctx.message.channel.send(error);

@handle_delete_emoji.error
async def handle_delete_emoji_error(ctx, error):
    await ctx.message.channel.send(error)

# this just creates the emoji on the server
# will overwrite the previous emoji if there was one under its name
async def handle_create_emoji(ctx, image, name):
    overwrite = False
    guild = ctx.message.guild

    for emoji in guild.emojis:
        if emoji.name == name:
            overwrite = True
            await emoji.delete()
            break

    emoji = await guild.create_custom_emoji(name=name, image=image)
    if overwrite == True:   
        await ctx.message.channel.send("Emoji overwritten! Use `:{}:` to use {}.".format(emoji.name, str(emoji)))
    else:
        await ctx.message.channel.send("Emoji added! Use `:{}:` to use {}.".format(emoji.name, str(emoji)))
    return

# error sounds cooler than exception for users
class Error(Exception):
    pass

bot.run(config.token, reconnect=True)