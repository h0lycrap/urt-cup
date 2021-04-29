import discord
from dotenv import load_dotenv
load_dotenv()
import os
import mariadb
import logging


conn = mariadb.connect(
        user="dev",
        password=os.getenv('DBPASSWORD'),
        host=os.getenv('DBIP'),
        port=3306,
        database='urtcup'
    )
cursor = conn.cursor()

intents = discord.Intents.all()
client = discord.Client(intents=intents)

role_unregistered_id = 836897738796826645


###############COMMANDS########################################

async def command_zmb(message):
    await message.channel.send("Va dormir Zmb.")

async def command_lytchi(message):
    await message.channel.send("Toi aussi va dormir.")

async def command_st0mp(message):
    await message.channel.send("Mais oui toi aussi tu as une commande.")

async def command_holycrap(message):
    await message.channel.send("https://bit.ly/3nkl9FA")

async def command_urt5(message):
    await message.channel.send("soon (tm)")

async def command_createteam(message):
    await message.channel.send("Check your dms \U0001F60F")
    await message.author.send("Salut bg")

async def command_register(message):
    #Check if user is already registered
    cursor.execute("SELECT urt_auth FROM Users WHERE discord_id = %s;", (message.author.id,)) 
    if cursor.fetchone():
        await message.channel.send("User already registered.")
        return

    #Check if there are 2 arguments
    args = message.content.split('!register')[1].strip().split(" ")
    if len(args) != 2:
        await message.channel.send("Please specify your urt auth and in-game name (case sensitive): \n``!register <auth> <in-game name>``")
        return

    #Check if auth is already registered
    cursor.execute("SELECT discord_id FROM Users WHERE urt_auth = %s", (args[0],))   
    if cursor.fetchone():
        await message.channel.send("Auth already registered.")
        return

    #Check if ingame name is already taken
    cursor.execute("SELECT discord_id FROM Users WHERE urt_auth = %s", (args[1],))   
    if cursor.fetchone():
        await message.channel.send("In-game name already taken.")
        return

    #Add user to DB and remove unregistered role
    cursor.execute("INSERT INTO Users(discord_id, urt_auth, ingame_name) VALUES (%s, %s, %s) ;", (message.author.id, args[0], args[1]))
    conn.commit()
    await message.channel.send("User successfully registered.")
    await message.author.remove_roles(discord.utils.get(client.guilds[0].roles, id=role_unregistered_id))

    #There can be permission errors if the user's role is higher in hierarchy than the bot
    try:
        await message.author.edit(nick=args[1])
    except Exception as e:
        pass


#################EVENTS###################################

@client.event
async def on_message(message):
    #Check if the message is a dm or if the author is the bot
    if message.guild == None or message.author == client.user:
        return

    if message.content.startswith('!zmb'):
        await command_zmb(message)
        return

    if message.content.startswith('!lytchi'):
        await command_lytchi(message)
        return

    if message.content.startswith('!st0mp'):
        await command_st0mp(message)
        return

    if message.content.startswith('!holy'):
        await command_holycrap(message)
        return

    if message.content.startswith('!urt5'):
        await command_urt5(message)
        return

    if message.content.startswith('!createteam'):
        await command_createteam(message)
        return

    if message.channel == discord.utils.get(message.guild.channels, name="register") and message.content.startswith('!register'):
        await command_register(message)
        return

@client.event
async def on_member_join(member):
    #Check if user is already registered and rename them if yes
    cursor.execute("SELECT ingame_name FROM Users WHERE discord_id = %s", (member.id,))   
    for name in cursor:
        await member.edit(nick=name[0])
        return

    await member.add_roles(discord.utils.get(client.guilds[0].roles, id=role_unregistered_id))

@client.event
async def on_ready():
    print("Bot online")
    await client.change_presence(activity=discord.Game(name="Urban Terror"))    

client.run(os.getenv('TOKEN'))

