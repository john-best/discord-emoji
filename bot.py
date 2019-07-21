import discord
from discord.ext import commands
import requests
import re
import asyncio

import config

prefix = "!"
bot = commands.Bot(command_prefix=commands.when_mentioned_or(prefix))
bot.remove_command("help")

emoji_regex = "^<:(?P<name>[A-zA-Z0-9]*):(?P<id>[0-9]*)>$"
emoji_regex2 = "^:(?P<name>[A-zA-Z0-9]*):$"
bot_url = "https://github.com/john-best/discord-emoji"

@bot.event
async def on_ready():
    # change the presence
    await bot.change_presence(activity=discord.Game(f"{prefix}emoji_help for Emoji Abuse"))

"""
emoji_add - adds/overwrites an emoji to the server

to use:
1. emoji_add url actual_url
2. emoji_add twitch twitch_channel twitch_emote_name [optional: custom_emote_name]
3. emoji_add ffz ffz_user ffz_emote_name [optional: custom_emote_name]
4. emoji_add ffzid ffz_emote_id [optional: custom_emote_name]
5. emoji_add bttv bttv_user bttv_emote_name [optional: custom_emote_name]
6. emoji_add twitchg twitch_emote_name [optional: custom_emote_name]
7. emoji_add bttvg bttv_emote_name [optional: custom_emote_name]

note: both the bot and the user must have the manage_emojis permissions
"""
@bot.command(name="emoji_add")
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

    elif args[0] == "twitchg":
        
        # prob cache this in the future
        url = "https://twitchemotes.com/api_cache/v3/global.json"
        emoticons = requests.get(url).json()

        name = args[1]

        # in situations where the user can type the emoji
        # the emoji is replaced with <:name:id>, so we need to extract the name
        match = re.match(emoji_regex, name)
        if match is not None:
            name = match.group("name")

        if name not in emoticons:
            await ctx.channel.send("Error: twitch global emote not found!")
            return

        url = f"https://static-cdn.jtvnw.net/emoticons/v1/{emoticons[name]['id']}/1.0"
        image = requests.get(url).content

        # custom name (ignore rest of the args if there are any more)
        if len(args) >= 3:
            name = args[2]
                
        await handle_create_emoji(ctx, image, name)
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
            return
        
        emote_url = f"https://cdn.betterttv.net/emote/{emote_id}/3x"
        image = requests.get(emote_url).content

        # custom name (ignore rest of the args if there are any more)
        if len(args) >= 4:
            name = args[3]

        await handle_create_emoji(ctx, image, name)
        return

    # bttvg emote_name
    elif args[0] == "bttvg":
        url = f"https://api.betterttv.net/2/emotes"
        name = args[1]
        res = requests.get(url).json()
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
            await ctx.channel.send("Error: unable to find BetterTTV global emote!")
            return
        
        emote_url = f"https://cdn.betterttv.net/emote/{emote_id}/3x"
        image = requests.get(emote_url).content

        # custom name (ignore rest of the args if there are any more)
        if len(args) >= 3:
            name = args[2]

        await handle_create_emoji(ctx, image, name)
        return

    # if you didn't type in url/twitch(g)/ffz/bttv(g) then what platform are you looking for
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
@bot.command(name="emoji_help")
async def handle_emoji_help(ctx):
    description = """
    Here are the commands that I know.

    `emoji_add twitch/ffz/bttv channelname emotename [optional: customname]`
    `emoji_add twitchg/bttvg emotename [optional: customname]`
    `emoji_add ffzid emote_id [optional: customname]`
    `emoji_add url url emotename`
    `emoji_delete emotename`
    `emoji_list`
    `emoji_info emoji`
    `emoji_rename emoji newname`
    `emoji_set_roles emoji role1 role2 role3...` (their ids)
    `emoji_server_roles`
    `emoji_help` (this!)

    Please note that both you and the bot (me!) need to have emoji editing permissions.
    """
    embed = discord.Embed(description=description, color=0x5bc0de)
    embed.set_author(name="Emoji Discord Bot", url=bot_url, icon_url=bot.user.avatar_url)
    await ctx.channel.send(embed=embed)

"""
emoji_info - prints out info regarding the emoji

to use:
1. emoji_info emoji
"""
@bot.command(name="emoji_info")
async def handle_emoji_info(ctx, *args):
    if len(args) != 1:
        await ctx.channel.send(f"Error: Expected exactly 1 arg. Found {len(args)}.")
        return

    match = re.match(emoji_regex, args[0])
    id = -1
    if match is not None:
        id = match.group("id")
    
    if id == -1:
        match = re.match(emoji_regex2, args[0])
        if match is not None:
            for emoji in ctx.guild.emojis:
                if emoji.name == match.group("name"):
                    id = emoji.id
                    break

    emoji = bot.get_emoji(int(id))

    if emoji == None:
        await ctx.channel.send(f"Error: emoji not found! Input must be an emoji within this server.")
        return

    embed = discord.Embed(title=f"Emoji info for {emoji.name}", color=0x5bc0de)
    embed.set_image(url=emoji.url)
    embed.add_field(name="ID", value=emoji.id)
    embed.add_field(name="Server", value=emoji.guild)
    embed.add_field(name="Created At", value=emoji.created_at)
    embed.add_field(name="Role Restricted?", value="No" if emoji.roles == [] else f"Yes. {[role.name for role in emoji.roles]}")
    await ctx.channel.send(embed=embed)

"""
emoji_rename - renames an emoji

to use:
1. emoji_rename emoji new_name

note: both the bot and the user must have the manage_emojis permissions
note2: don't need :colons: for new_name
"""
@commands.has_permissions(manage_emojis=True)
@commands.bot_has_permissions(manage_emojis=True)
@bot.command(name="emoji_rename")
async def handle_emoji_rename(ctx, *args):
    if len(args) != 2:
        await ctx.channel.send(f"Error: Expected exactly 2 args. Found {len(args)}.")
        return
    
    match = re.match(emoji_regex, args[0])
    id = -1
    if match is not None:
        id = match.group("id")

    if id == -1:
        match = re.match(emoji_regex2, args[0])
        if match is not None:
            for emoji in ctx.guild.emojis:
                if emoji.name == match.group("name"):
                    id = emoji.id
                    break

    emoji = bot.get_emoji(int(id))
    if emoji == None:
        await ctx.channel.send(f"Error: emoji not found! Input must be an emoji within this server.")
        return
    
    await asyncio.wait_for(emoji.edit(name=args[1]), timeout=3.0)
    await ctx.channel.send(f"Done! You can now use {emoji} by typing `:{args[1]}:`.")

"""
emoji_set_roles - set role permissions for emojis

to use:
1. emoji_set_roles emoji role_id1 role_id2...
2. emoji_set_roles emoji None

note: both the bot and the user must have the manage_emojis permissions
note2: you only need one role id at the minimum, or just None to make it open to everyone
"""
@commands.has_permissions(manage_emojis=True)
@commands.bot_has_permissions(manage_emojis=True)
@bot.command(name="emoji_set_roles")
async def handle_emoji_set_roles(ctx, *args):
    if len(args) < 2:
        await ctx.channel.send(f"Error: Expected at least 2 args. Found {len(args)}.")
        return
    
    match = re.match(emoji_regex, args[0])
    id = -1
    if match is not None:
        id = match.group("id")

    if id == -1:
        match = re.match(emoji_regex2, args[0])
        if match is not None:
            for emoji in ctx.guild.emojis:
                if emoji.name == match.group("name"):
                    id = emoji.id
                    break

    emoji = bot.get_emoji(int(id))
    if emoji == None:
        await ctx.channel.send(f"Error: emoji not found! Input must be an emoji within this server.")
        return

    roles = args[1:]
    if roles[0] == "None":
        roles = []
    else:
        roles = [ctx.guild.get_role(int(role)) for role in roles]

    await emoji.edit(name=emoji.name, roles=roles)
    await ctx.channel.send(f"Done! Emoji roles for {emoji} have been updated.")

"""
emoji_server_roles - prints out the server roles and their corresponding ids

to use:
1. emoji_server_roles

note: this command exists because there's no easy way to get role ids if the role isn't @mentionable
"""
@bot.command(name="emoji_server_roles")
async def handle_emoji_server_roles(ctx):

    embed = discord.Embed(title=f"Server Roles for {ctx.guild}", color=0x5bc0de)

    for role in ctx.guild.roles:
        if role.name != "@everyone":
            embed.add_field(name=role.name, value=role.id)
    
    await ctx.channel.send(embed=embed)

"""
We'll send errors related to these commands to the channel.
All others will be sent into console since they're probably not that important.
"""
@handle_emoji.error
async def handle_emoji_error(ctx, error):
    await ctx.channel.send(error)

@handle_emoji_delete.error
async def handle_emoji_delete_error(ctx, error):
    await ctx.channel.send(error)

@handle_emoji_list.error
async def handle_emoji_list_error(ctx, error):
    await ctx.channel.send(error)

@handle_emoji_info.error
async def handle_emoji_info_error(ctx, error):
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
