import discord
from discord.ext import commands
import requests
import re
import asyncio

import config

prefix = "&"
bot = commands.Bot(command_prefix=commands.when_mentioned_or(prefix))
bot.remove_command("help")

emoji_regex = "^<:(?P<name>[A-zA-Z0-9]*):(?P<id>[0-9]*)>$"
emoji_regex2 = "^:(?P<name>[A-zA-Z0-9]*):$"
bot_url = "https://github.com/john-best/discord-emoji"

@bot.event
async def on_ready():
    # change the presence
    await bot.change_presence(activity=discord.Game(f"{prefix}help for Emoji Abuse"))

"""
emoji - adds/overwrites an emoji to the server

to use:
1. emoji url actual_url
2. emoji twitch twitch_channel twitch_emote_name [optional: custom_emote_name]
3. emoji ffz ffz_user ffz_emote_name [optional: custom_emote_name]
4. emoij ffzid ffz_emote_id [optional: custom_emote_name]
5. emoji bttv bttv_user bttv_emote_name [optional: custom_emote_name]

note: both the bot and the user must have the manage_emojis permissions
"""
@bot.command(name="emoji")
@commands.has_permissions(manage_emojis=True)
@commands.bot_has_permissions(manage_emojis=True)
async def handle_emoji(ctx, *args):
    
    # this will turn off typing... in 10 seconds
    # ffz might take longer, but the bot should always return a success or an error eventually
    await ctx.channel.trigger_typing()

    # arg length check. maximum doesn't really matter since we just ignore it
    if len(args) < 2:
        await ctx.channel.send(f"Error: Expected at least 2 args, found {len(args)}.")
        return

    # url actual_url emote_name
    if args[0] == "url":
        name = args[2]
        url = args[1]

        image = requests.get(url).content
        await handle_create_emoji(ctx, image, name)
        return
    
    # twitch username emote_name
    elif args[0] == "twitch":
        url = f"https://api.twitch.tv/api/channels/{args[1]}/product"
        name = args[2]

        res = requests.request("GET", url=url, headers={"Client-ID": config.twitch_client_id}).json()
        
        if "status" in res and res["status"] == 404:
            await ctx.channel.send("Error: twitch channel not found!")
            return

        emoticons = res["emoticons"]
        
        # in situations where the user can type the emoji
        # the emoji is replaced with <:name:id>, so we need to extract the name
        match = re.match(emoji_regex, name)
        if match is not None:
            name = match.group("name")
        
        # find the emote from the emote list of the channel
        for emoticon in emoticons:
            if emoticon["regex"] == name:
                url = emoticon["url"]
                image = requests.get(url).content

                # custom name (ignore rest of the args if there are any more)
                if len(args) >= 4:
                    name = args[3]

                await handle_create_emoji(ctx, image, name)
                return
            
        # emote not found
        await ctx.channel.send("Error: twitch emote not found!")
        return

    # ffz username emote_name
    elif args[0] == "ffz":
        name = args[2]

        # in situations where the user can type the emoji
        # the emoji is replaced with <:name:id>, so we need to extract the name
        match = re.match(emoji_regex, name)
        if match is not None:
            name = match.group("name")

        # search using channel name AND the search parameter
        url = f"https://api.frankerfacez.com/v1/emoticons?q={args[1]}%20{name}"
        emoticons = requests.get(url).json()["emoticons"]

        # if the search query returns nothing, then we can't do anything
        if len(emoticons) == 0:
            await ctx.channel.send("Error: unable to find FFZ emote with given channel name and emote name")
            return
        
        # there might be a situation where the search could return multiple emotes
        # however, given a channel/user name and the emote name, only one should
        # appear. we'll assume only 1 emote exists
        emoticon = emoticons[0]

        # go for highest quality image first
        image_url = ""
        if "4" in emoticon["urls"]:
            image_url = emoticon["urls"]["4"]
        elif "2" in emoticon["urls"]:
            image_url = emoticon["urls"]["2"]
        else:
            image_url = emoticon["urls"]["1"]
        image = requests.get(f"https:{image_url}").content

        # custom name (ignore rest of the args if there are any more)
        if len(args) >= 4:
            name = args[3]
        
        await handle_create_emoji(ctx, image, name)
        return

    # ffzid emote_id
    elif args[0] == "ffzid":
        emote_id = args[1]

        # there is an api call for directly the id, which is faster than using search
        url = f"https://api.frankerfacez.com/v1/emote/{emote_id}"
        res = requests.get(url).json()

        # error out if id doesn't exist
        if "error" in res:
            await ctx.channel.send("Error: unable to find FrankerFaceZ emote given the id!")
            return
        
        emote = res["emote"]
        image_url = ""
        if "4" in emote["urls"]:
            image_url = emote["urls"]["4"]
        elif "2" in emote["urls"]:
            image_url = emote["urls"]["2"]
        else:
            image_url = emote["urls"]["1"]
        image = requests.get(f"https:{image_url}").content

        name = emote["name"]
        if len(args) >= 3:
            name = args[2]
        
        await handle_create_emoji(ctx, image, name)
        return       

    # bttv channel_name emote_name
    elif args[0] == "bttv":
        url = f"https://api.betterttv.net/2/channels/{args[1]}"
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

        # grab the id string if the emote exists
        emote_id = None

        for emote in emotes:
            if emote["code"] == name:
                emote_id = emote["id"]
                break

        # the emote didn't exist so we didn't get an id
        if emote_id is None:
            await ctx.channel.send("Error: unable to find BetterTTV emote with given channel name and emote name")
        
        emote_url = f"https://cdn.betterttv.net/emote/{emote_id}/1x"
        image = requests.get(emote_url).content

        # custom name (ignore rest of the args if there are any more)
        if len(args) >= 4:
            name = args[3]

        await handle_create_emoji(ctx, image, name)
        return

    # if you didn't type in url/twitch/ffz/bttv then what platform are you looking for
    await ctx.channel.send(f"Error: Invalid args. Check {ctx.prefix}help for more information.")

"""
emoji_delete - deletes emoji from the server

to use:
1. emoji_delete emoji_name
emoji_name will probably look like <id:name> or :name: so we'll just strip it if it is

note: both the bot and the user must have the manage_emojis permissions
"""
@bot.command(name="emoji_delete")
@commands.has_permissions(manage_emojis=True)
@commands.bot_has_permissions(manage_emojis=True)
async def handle_emoji_delete(ctx, name):
    await ctx.channel.trigger_typing()

    # if we want to delete an emoji it"s most likely (100%??) going to pass through these conversions
    match = re.match(emoji_regex, name)
    if match is not None:
        name = match.group("name")
    
    match = re.match(emoji_regex2, name)
    if match is not None:
        name = match.group("name")

    for emoji in ctx.guild.emojis:
        if emoji.name == name:
            await emoji.delete()
            await ctx.channel.send(f"`:{name}:` deleted.")
            return
    
    await ctx.channel.send(f"Error: could not find `:{name}:`.")

"""
emoji_list - prints an embed of the emojis on the server

you can delete this embed within 10 seconds if you want
NOT TESTED: embed hits the character limit, will probably error out
"""
@commands.bot_has_permissions(add_reactions=True, manage_messages=True)
@bot.command("emoji_list")
async def handle_emoji_list(ctx):

    def check(reaction, user):
        return user == ctx.message.author and str(reaction.emoji) == "❌"

    embed = discord.Embed(title="Emoji List", color=0x5bc0de)
    embed.set_author(name="Emoji Discord Bot", url=bot_url, icon_url=bot.user.avatar_url)

    for emoji in ctx.guild.emojis:
        embed.add_field(name=f":{emoji.name}:", value=str(emoji))

    sent = await ctx.channel.send(embed=embed)
    await sent.add_reaction("❌")

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=10.0, check=check)
    except asyncio.TimeoutError:
        await sent.clear_reactions()
    else:
        await sent.delete()
        await ctx.message.delete()


"""
help - sends the help embed into channel
"""
@bot.command(name="help")
async def handle_help(ctx):
    description = """
    Here are the commands that I know.

    `emoji twitch/ffz/bttv channelname emotename [optional: customname]`
    `emoji ffzid emote_id [optional: customname]`
    `emoji url emotename`
    `emoji_delete emotename`
    `emoji_list`
    `help` (this!)

    Please note that both you and I will need to have emoji editing permissions.
    """
    embed = discord.Embed(description=description, color=0x5bc0de)
    embed.set_author(name="Emoji Discord Bot", url=bot_url, icon_url=bot.user.avatar_url)
    await ctx.channel.send(embed=embed)


"""
We'll send errors related to these commands to the channel.
All others will be sent into console since they're probably not that important.
"""
@handle_emoji.error
async def handle_emoji_error(ctx, error):
    await ctx.channel.send(error);

@handle_emoji_delete.error
async def handle_emoji_delete_error(ctx, error):
    await ctx.channel.send(error)

@handle_emoji_list.error
async def handle_emoji_list_error(ctx, error):
    await ctx.channel.send(error)


"""
helper method for creating a custom emoji on the server
since we use this for url, twitch, ffz, bttv
"""
async def handle_create_emoji(ctx, image, name):
    overwrite = False

    for emoji in ctx.guild.emojis:
        if emoji.name == name:
            overwrite = True
            await emoji.delete()
            break

    emoji = await ctx.guild.create_custom_emoji(name=name, image=image)
    if overwrite == True:   
        await ctx.channel.send(f"Emoji overwritten! Use `:{emoji.name}:` to use {str(emoji)}.")
    else:
        await ctx.channel.send(f"Emoji added! Use `:{emoji.name}:` to use {str(emoji)}.")
    return

# error sounds cooler than exception for users
class Error(Exception):
    pass

# reconnect=True for auto reconnect
bot.run(config.token, reconnect=True)