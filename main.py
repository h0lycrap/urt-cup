import discord
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()
import os
import mariadb
import json
import asyncio
import cogs.common.update as update
import cogs.common.check as check
from ftwgl import FTWClient

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption


# Init bot and remove default help cmd
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents) 
bot.remove_command('help')

# Connect to DB
bot.conn = mariadb.connect(
        user="dev",
        password=os.getenv('DBPASSWORD'),
        host=os.getenv('DBIP'),
        port=3306,
        database=os.getenv('DBNAME')
    )
bot.cursor = bot.conn.cursor(dictionary=True)

bot.ftw = FTWClient(
    ftw_api_key=os.getenv("FTW_API_KEY"),
    ftw_host=os.getenv("FTW_HOST")
)


# Cogs cmds 
@bot.command()
@check.is_guild_manager()
async def load(ctx, extension):
    bot.load_extension(f'cogs.{extension}')

@bot.command()
@check.is_guild_manager()
async def unload(ctx, extension):
    bot.unload_extension(f'cogs.{extension}')


# Get Alfred's script
afred_quotes_loc = "data/alfred_quotes.json"
with open( afred_quotes_loc, 'rb' ) as json_alfred_quotes :
    bot.quotes = json.load( json_alfred_quotes )

# Init async loop
bot.async_loop = asyncio.get_event_loop()

bot.number_emojis = []

bot.message_welcome_id = int(os.getenv('message_welcome_id'))

bot.role_unregistered_id = int(os.getenv('role_unregistered_id'))
bot.role_captains_id = int(os.getenv('role_captains_id'))
bot.role_flawless_crew_id = int(os.getenv('role_flawless_crew_id'))
bot.role_cup_supervisor_id = int(os.getenv('role_cup_supervisor_id'))
bot.role_moderator_id = int(os.getenv('role_moderator_id'))
bot.role_streamer_id = int(os.getenv('role_streamer_id'))
bot.role_bot_id = int(os.getenv('role_bot_id'))

bot.channel_log_id = int(os.getenv('channel_log_id'))
bot.channel_demolog_id = int(os.getenv('channel_demolog_id'))
bot.channel_roster_id = int(os.getenv('channel_roster_id'))
bot.channel_panel_id = int(os.getenv('channel_panel_id'))

bot.category_match_schedule_id = int(os.getenv('category_match_schedule_id'))

bot.max_players_per_team = 8
bot.users_busy = []
bot.fixtures_busy = []

bot.urtli_id = os.getenv('urtli_id')
bot.urtli_pass = os.getenv('urtli_pass')

@bot.event
async def on_member_join(member):
    #Check if user is already registered and rename them if yes
    bot.cursor.execute("SELECT ingame_name FROM Users WHERE discord_id = %s", (member.id,))   
    for name in bot.cursor:
        await member.edit(nick=name['ingame_name'])
        return

    await member.add_roles(discord.utils.get(bot.guilds[0].roles, id=bot.role_unregistered_id))

@bot.event
async def on_member_remove(member):
    #Get user info
    bot.cursor.execute("SELECT * FROM Users WHERE discord_id = %s", (member.id,)) 
    user_info = bot.cursor.fetchone()
    log_channel =  discord.utils.get(bot.guilds[0].channels, id=bot.channel_log_id)
    if user_info:
        await log_channel.send(f":exclamation: {user_info['ingame_name']} [``{user_info['urt_auth']}``] left the discord")
    else:
        await log_channel.send(f":exclamation: **{member} (not registered) left the discord**")



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


    print("Bot online")
    #welcome_chan = discord.utils.get(bot.guilds[0].channels, name="welcome")
    #await welcome_chan.send(content=":interrobang:  **Invite your mates :** \n             Feel free to use this permanent link : https://discord.gg/DBJjn3erzz")
    #await welcome_chan.send(content="\u200b", components=[Button(style=ButtonStyle.green, label="Click here to register", custom_id="button_register")])

    '''
    pannel_chan = discord.utils.get(bot.guilds[0].channels, id=bot.channel_panel_id)
    
    await pannel_chan.send(content=":white_check_mark: **Create a clan** \n\nClick the button below to start the team creation process. I will dm you and ask you:\n- The ``clan name``  *(must be unique)*\n- The ``clan tag`` *(must be unique)*\n- The ``clan nationality`` *(use flag emojis  :flag_fr:  only)*\n\n:x:  to cancel dm !cancel anytime during the creation process", 
                           components=[[
                                Button(style=ButtonStyle.green, label="Create a clan", custom_id="button_create_clan")
                                ]])
    
    
    await pannel_chan.send(content=":pencil: **Edit a clan** \n\nClick the button below to edit the clan of your choice:\n- ``Invite`` a player to join your clan. \n:exclamation: **Each invited player needs to be on this discord and must have finalized the registration process** \n\n- ``Remove`` a player from your clan. \n:exclamation: **You can't remove yourself from the clan, contact an admin if you want to delete your clan**\n\n- Mark a player as ``active/inactive``\n\n- Change the clan ``captain``\n:exclamation: **This action is irreversible** \n\n- Edit the ``flag``,  ``discord invitation link``,  ``clan name`` and ``tag`` of your clan", 
                           components=[[
                                Button(style=ButtonStyle.blue, label="Edit a clan", custom_id="button_edit_clan")
                                ]])
    
    
    await pannel_chan.send(content="**Leave a clan**\n\nClick the button below to leave the clan of your choice.\n:exclamation:**You can't leave a clan you are captain of, contact an admin to delete your clan or change clan captain**", 
                           components=[[
                                Button(style=ButtonStyle.red, label="Leave a clan", custom_id="button_leave_clan")
                                ]])
    '''
    
bot.run(os.getenv('TOKEN'))
