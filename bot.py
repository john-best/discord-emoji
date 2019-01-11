import discord
from discord.ext import commands
import requests
import re
import asyncio

import config

bot = commands.Bot(command_prefix='&')
bot.remove_command('help')

emoji_regex = "^<:(?P<name>[A-zA-Z0-9]*):(?P<id>[0-9]*)>$"
emoji_regex2 = "^:(?P<name>[A-zA-Z0-9]*):$"

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='{}help for Emoji Abuse'.format(bot.command_prefix)))
    pass

@bot.command(name="help")
async def handle_help(ctx):
    description = """
    Here are the commands that I know.

    `emoji twitch/ffz/bttv channelname emotename [optional: customname]`
    `emoji url emotename`
    `emoji_delete emotename`
    `emoji_list`
    `help` (this!)

    Please note that both you and I will need to have emoji editing permissions.
    """
    embed = discord.Embed(description=description, color=0x5bc0de)
    embed.set_author(name="Emoji Discord Bot", url="https://github.com/john-best/discord-emoji", icon_url=bot.user.avatar_url)
    await ctx.channel.send(embed=embed)


# emoji [url/twitch/ffz] [username/url] [twitch/ffz emote if not url]
# bot AND caller needs to have manage emojis permission
@bot.command(name="emoji")
@commands.has_permissions(manage_emojis=True)
@commands.bot_has_permissions(manage_emojis=True)
async def handle_emoji(ctx, *args):
    # two options:
    # emoji url actual_url emote_name
    # emoji twitch/ffz/bttv username emote_name [optional: custom_emote_name]

    await ctx.channel.trigger_typing()
    if len(args) < 3:
        await ctx.channel.send("Error: Expected at least 3 args, found {}.".format(len(args)))
        return

    # url actual_url emote_name
    if args[0] == 'url':
        name = args[2]
        url = args[1]

        image = requests.get(url).content
        await handle_create_emoji(ctx, image, name)
        return
    
    # twitch username emote_name
    elif args[0] == 'twitch':
        url = "https://api.twitch.tv/api/channels/{}/product".format(args[1])
        name = args[2]

        res = requests.request('GET', url=url, headers={"Client-ID": config.twitch_client_id}).json()
        
        if "status" in res and res["status"] == 404:
            await ctx.channel.send("Error: twitch channel not found!")
            return

        emoticons = res["emoticons"]
        
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
                if len(args) == 4:
                    name = args[3]
                await handle_create_emoji(ctx, image, name)
                return
              
        await ctx.channel.send("Error: twitch emote not found!")
        return

    # ffz username emote_name
    elif args[0] == 'ffz':
        name = args[2]

        # in situations where the user can type the emoji
        # the emoji is replaced with <:name:id>
        match = re.match(emoji_regex, name)
        if match is not None:
            name = match.group("name")


        # search using channel name AND the search parameter
        url = "https://api.frankerfacez.com/v1/emoticons?q={}%20{}".format(args[1], name)
        emoticons = requests.get(url).json()["emoticons"]

        if len(emoticons) == 0:
            await ctx.channel.send("Error: unable to find FFZ emote with given channel name and emote name")
            return
        
        emoticon = emoticons[0]

        # when would we use the urls not located at the first location?
        image_url = emoticon["urls"]["1"]
        image = requests.get("https:{}".format(image_url)).content

        # custom name
        if len(args) == 4:
            name = args[3]
        await handle_create_emoji(ctx, image, name)

        # TODO: what happens when there are more than 1 result?
        # although given the channel name and emote name, only one should show up
        # this is probably low priority. maybe someday we can search on ffz using this bot!

        return

    # bttv
    elif args[0] == 'bttv':
        url = "https://api.betterttv.net/2/channels/{}".format(args[1])
        name = args[2]
        res = requests.get(url).json()

        if res["status"] == "404":
            await ctx.channel.send("Error: unable to find BetterTTV channel")
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
            await ctx.channel.send("Error: unable to find BetterTTV emote with given channel name and emote name")
        
        emote_url = "https://cdn.betterttv.net/emote/{}/1x".format(emote_id)
        image = requests.get(emote_url).content

        # custom name
        if len(args) == 4:
            name = args[3]
        await handle_create_emoji(ctx, image, name)

    else:
        await ctx.channel.send("Error: Invalid args. Check {}help for more information.".format(ctx.prefix))
        return

@bot.command(name="emoji_delete")
@commands.has_permissions(manage_emojis=True)
@commands.bot_has_permissions(manage_emojis=True)
async def handle_delete_emoji(ctx, name):
    await ctx.channel.trigger_typing()

    # if we want to delete an emoji it's most likely (100%??) going to pass through these conversions
    match = re.match(emoji_regex, name)
    if match is not None:
        name = match.group("name")
    
    match = re.match(emoji_regex2, name)
    if match is not None:
        name = match.group("name")

    for emoji in ctx.guild.emojis:
        if emoji.name == name:
            await emoji.delete()
            await ctx.channel.send("`:{}:` deleted.".format(name))
            return
    
    await ctx.channel.send("Error: could not find `:{}:`.".format(name))
# basic error handling to send to channel for easier debugging
@handle_emoji.error
async def handle_emoji_error(ctx, error):
    await ctx.channel.send(error);

@handle_delete_emoji.error
async def handle_delete_emoji_error(ctx, error):
    await ctx.channel.send(error)

# this just creates the emoji on the server
# will overwrite the previous emoji if there was one under its name
async def handle_create_emoji(ctx, image, name):
    overwrite = False

    for emoji in ctx.guild.emojis:
        if emoji.name == name:
            overwrite = True
            await emoji.delete()
            break

    emoji = await ctx.guild.create_custom_emoji(name=name, image=image)
    if overwrite == True:   
        await ctx.channel.send("Emoji overwritten! Use `:{}:` to use {}.".format(emoji.name, str(emoji)))
    else:
        await ctx.channel.send("Emoji added! Use `:{}:` to use {}.".format(emoji.name, str(emoji)))
    return

# prints list of emoji, u can delete this embed within 10 seconds if you want
@commands.bot_has_permissions(add_reactions=True, manage_messages=True)
@bot.command("emoji_list")
async def handle_emoji_list(ctx):

    def check(reaction, user):
        return user == ctx.message.author and str(reaction.emoji) == '❌'

    embed = discord.Embed(title="Emoji List", color=0x5bc0de)
    embed.set_author(name="Emoji Discord Bot", url="https://github.com/john-best/discord-emoji", icon_url=bot.user.avatar_url)

    for emoji in ctx.guild.emojis:
        embed.add_field(name=":{}:".format(emoji.name), value=str(emoji))

    sent = await ctx.channel.send(embed=embed)
    await sent.add_reaction('❌')

    try:
        reaction, user= await bot.wait_for('reaction_add', timeout=10.0, check=check)
    except asyncio.TimeoutError:
        await sent.clear_reactions()
    else:
        await sent.delete()
        await ctx.message.delete()

# error sounds cooler than exception for users
class Error(Exception):
    pass

bot.run(config.token, reconnect=True)