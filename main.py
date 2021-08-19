import discord
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()
import os
import mariadb
import json
import asyncio
import cogs.common.update as update

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption


# Init bot and remove default help cmd
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents) #discord.bot(intents=intents)
bot.remove_command('help')

# Connect to DB
bot.conn = mariadb.connect(
        user="dev",
        password=os.getenv('DBPASSWORD'),
        host=os.getenv('DBIP'),
        port=3306,
        database='flawlessdb'
    )
bot.cursor = bot.conn.cursor(dictionary=True)


# Cogs cmds # TODO make them admin only
@bot.command()
async def load(ctx, extension):
    bot.load_extension(f'cogs.{extension}')
@bot.command()
async def unload(ctx, extension):
    bot.unload_extension(f'cogs.{extension}')


# Get Alfred's script
afred_quotes_loc = "data/alfred_quotes.json"
with open( afred_quotes_loc, 'rb' ) as json_alfred_quotes :
    bot.quotes = json.load( json_alfred_quotes )

# Init async loop
bot.async_loop = asyncio.get_event_loop()

# Init global variables
#number_emojis = [u"\U00000031\U0000FE0F\U000020E3", u"\U00000032\U0000FE0F\U000020E3", u"\U00000033\U0000FE0F\U000020E3", u"\U00000034\U0000FE0F\U000020E3", u"\U00000035\U0000FE0F\U000020E3", u"\U00000036\U0000FE0F\U000020E3", u"\U00000037\U0000FE0F\U000020E3", u"\U00000038\U0000FE0F\U000020E3", u"\U00000039\U0000FE0F\U000020E3", u"\U0001F51F"]
#letter_emojis = [u"\U0001F1E6", u"\U0001F1E7", u"\U0001F1E8", u"\U0001F1E9", u"\U0001F1EA", u"\U0001F1EB", u"\U0001F1EC", u"\U0001F1ED", u"\U0001F1EE", u"\U0001F1EF", u"\U0001F1F0", u"\U0001F1F1", u"\U0001F1F2", u"\U0001F1F2", u"\U0001F1F3", u"\U0001F1F4", u"\U0001F1F5", u"\U0001F1F6", u"\U0001F1F7", u"\U0001F1F8", u"\U0001F1F9", u"\U0001F1FA", u"\U0001F1FB", u"\U0001F1FC", u"\U0001F1FD", u"\U0001F1FE", u"\U0001F1FF"]
bot.number_emojis = []

bot.message_welcome_id = 838861660805791825

bot.role_unregistered_id = 836897738796826645
bot.role_captains_id = 839893529517228113
bot.role_flawless_crew_id = 839651903298207816
bot.role_cup_supervisor_id = 836901156642226196

bot.channel_log_id = 834947952023437403
bot.channel_roster_id = 834931256918802512
bot.channel_panel_id = 877269587287236698

bot.category_match_schedule_id = 835237146225934426

bot.max_players_per_team = 8
bot.users_busy = []
bot.fixtures_busy = []

@bot.event
async def on_member_join(member):
    #Check if user is already registered and rename them if yes
    bot.cursor.execute("SELECT ingame_name FROM Users WHERE discord_id = %s", (member.id,))   
    for name in bot.cursor:
        await member.edit(nick=name['ingame_name'])
        return

    await member.add_roles(discord.utils.get(bot.guilds[0].roles, id=bot.role_unregistered_id))



@bot.event
async def on_ready():
    # Temporary before discord py 2.0
    DiscordComponents(bot, change_discord_methods=True)

    for i in range(20): # to delete will disappear soon
        if i + 1 < 10:
            bot.number_emojis.append(discord.utils.get(bot.guilds[0].emojis, name=str(i + 1 ) + "_"))
        else:
            bot.number_emojis.append(discord.utils.get(bot.guilds[0].emojis, name=str(i + 1 )))

    await bot.change_presence(activity=discord.Game(name="Server Manager")) 

    # Load Cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')
            print(f'{filename[:-3]} loaded')

    # update
    bot.async_loop.create_task(update.roster(bot))
    bot.async_loop.create_task(update.signups(bot))

    print("Bot online")
    #welcome_chan = discord.utils.get(bot.guilds[0].channels, name="welcome")
    #await welcome_chan.send(content="Test", components=[Button(style=ButtonStyle.green, label="Click here to register", custom_id="button_register")])
    '''
    pannel_chan = discord.utils.get(bot.guilds[0].channels, id=bot.channel_panel_id)
    await pannel_chan.send(content="Click on a button to perform an action", 
                           components=[[
                                Button(style=ButtonStyle.blue, label="Create a clan", custom_id="button_create_clan"),
                                Button(style=ButtonStyle.grey, label="Edit a clan", custom_id="button_edit_clan")
                                ]])
    '''

bot.run(os.getenv('TOKEN'))


# to delete 
"""

# Commands executable in dm
dm_funcs = {'!editclan' : command_editclan, '!createclan' : command_createclan, '!signup' : command_signup, '!info' : command_info}

# Commands executable in channels
channel_funcs = {'!info' : command_info}

# Match channel commands
match_funcs = {'!schedule' : command_schedule, '!pickban' : command_pickban}

# Admin commands
admin_funcs = {'!createcup': command_createcup, '!fixture': command_fixture}

@bot.event
async def on_message(message):
    msg_split = message.content.split(" ", 1)

    # Check if the author is the bot
    if message.author == bot.user:
        print(1)
        return

    # DM and check if the user is busy
    if message.guild == None and msg_split[0] in dm_funcs and not (message.author.id in users_busy):
        await dm_funcs[msg_split[0]](message)
        print(2)
        return

    # Admin commands
    if message.guild != None and message.channel.id == channel_log_id and msg_split[0] in admin_funcs and not (message.author.id in users_busy):
        await admin_funcs[msg_split[0]](message)
        print(3)
        return

    # match commands
    fixture_category = discord.utils.get(guild.channels, id=category_match_schedule_id) 
    if  message.guild != None and message.channel.category == fixture_category and msg_split[0] in match_funcs:
        await match_funcs[msg_split[0]](message)
        print(4)
        return
    
    # Channel commands
    if  message.guild != None and msg_split[0] in channel_funcs:
        await channel_funcs[msg_split[0]](message)
        print(5)
        return
"""
