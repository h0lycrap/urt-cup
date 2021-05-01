import discord
from dotenv import load_dotenv
load_dotenv()
import os
import mariadb
import logging
import flag


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
channel_testbot_id = 834923278421721099

playersInTeamCreation = []


###############COMMANDS########################################

async def command_zmb(message):
    await message.channel.send("Va dormir Zmb.")
    await client.change_presence(activity=discord.CustomActivity(name="Server Manager")) 

async def command_lytchi(message):
    await message.channel.send("Toi aussi va dormir.")

async def command_st0mp(message):
    await message.channel.send("Mais oui toi aussi tu as une commande.")

async def command_holycrap(message):
    await message.channel.send("https://bit.ly/3nkl9FA")

async def command_urt5(message):
    await message.channel.send("soon (tm)")



async def command_createteam(message):
    # Check command validity
    if len(message.content) > 11:
        if message.content[11] != " ":
            return

    # Check if the user is already creating a team
    if message.author.id in playersInTeamCreation :
        await message.channel.send("You are already creating a team, check your dms.")
        return
    playersInTeamCreation.append(message.author.id)

    def check(m):
            return m.author == message.author and m.guild == None

    await message.channel.send("Check your dms \U0001F60F")

    await message.author.send("Follow the instructions to create your team, type ``cancel`` anytime to cancel the team creation.")

    name_checked = False
    while not name_checked:
        await message.author.send("Enter team name:")
        teamname_msg = await client.wait_for('message', check=check)

        if teamname_msg.content.lower() == 'cancel':
            await message.author.send("Team creation canceled.")
            playersInTeamCreation.remove(message.author.id)
            return

        # Check if team name is already taken
        cursor.execute("SELECT id FROM Teams WHERE name = %s", (teamname_msg.content,))   
        if cursor.fetchone():
            await message.author.send("Team name already taken.")
        else:
            name_checked = True
            

        
    tag_checked = False
    while not tag_checked:
        await message.author.send("Enter team tag:")
        tag_msg = await client.wait_for('message', check=check)

        if tag_msg.content.lower() == 'cancel':
            await message.author.send("Team creation canceled.")
            playersInTeamCreation.remove(message.author.id)
            return

        # Check if team tag is already taken
        cursor.execute("SELECT id FROM Teams WHERE tag = %s", (tag_msg.content,))   
        if cursor.fetchone():
            await message.author.send("Tag already taken.")
        else:
            tag_checked = True

    country_checked = False
    while not country_checked:
        await message.author.send("Enter team country (use flag emoji):")
        country_msg = await client.wait_for('message', check=check)

        if country_msg.content.lower() == 'cancel':
            await message.author.send("Team creation canceled.")
            playersInTeamCreation.remove(message.author.id)
            return

        cursor.execute("SELECT id FROM Countries WHERE id = %s;", (flag.dflagize(country_msg.content),))
        if not cursor.fetchone():
            await message.author.send("Invalid country.")
        else:
            country_checked = True


    cursor.execute("INSERT INTO Teams(name, tag, country, captain) VALUES (%s, %s, %s, %s) ;", (teamname_msg.content, tag_msg.content, flag.dflagize(country_msg.content), message.author.id))
    conn.commit()
    await message.author.send("Team successfully created.")
    playersInTeamCreation.remove(message.author.id)
    testbot_channel =  discord.utils.get(message.guild.channels, id=channel_testbot_id)
    await testbot_channel.send("New team created. Name: ``" + teamname_msg.content + '``\tTag: ``' + tag_msg.content + '``\tCountry: ' + country_msg.content + '\tCaptain: ' + f"<@{message.author.id}>", allowed_mentions=discord.AllowedMentions(users=False))



async def command_register(message):

    # Check command validity
    if len(message.content) > 9:
        if message.content[9] != " ":
            return

    # Check if user is already registered
    cursor.execute("SELECT urt_auth FROM Users WHERE discord_id = %s;", (message.author.id,)) 
    if cursor.fetchone():
        await message.channel.send("User already registered.")
        return

    # Check if there are 3 arguments
    args = message.content.split('!register')[1].strip().split(" ")
    if len(args) != 3:
        await message.channel.send("Please specify your urt auth, in-game name (case sensitive) and country (use flag emoji): \n``!register <auth> <in-game name> <country>``")
        return

    # Check if auth is already registered
    cursor.execute("SELECT discord_id FROM Users WHERE urt_auth = %s", (args[0],))   
    if cursor.fetchone():
        await message.channel.send("Auth already registered.")
        return

    # Check if ingame name is already taken
    cursor.execute("SELECT discord_id FROM Users WHERE ingame_name = %s", (args[1],))   
    if cursor.fetchone():
        await message.channel.send("In-game name already taken.")
        return

    cursor.execute("SELECT id FROM Countries WHERE id = %s;", (flag.dflagize(args[2]),))
    if not cursor.fetchone():
        await message.channel.send("Invalid country, please use a flag emoji.")
        return

    # Add user to DB and remove unregistered role
    cursor.execute("INSERT INTO Users(discord_id, urt_auth, ingame_name, country) VALUES (%s, %s, %s, %s) ;", (message.author.id, args[0], args[1], flag.dflagize(args[2])))
    conn.commit()
    await message.channel.send("User successfully registered.")
    await message.author.remove_roles(discord.utils.get(client.guilds[0].roles, id=role_unregistered_id))

    # There can be permission errors if the user's role is higher in hierarchy than the bot
    try:
        await message.author.edit(nick=args[1])
    except Exception as e:
        pass

async def command_addplayer(message):
    # Check command validity
    if len(message.content) > 10:
        if message.content[10] != " ":
            return

    # Check if there are 2 arguments
    args = message.content.split('!addplayer')[1].strip().split(" ")
    if len(args) != 2:
        await message.channel.send("Please specify the tag of the team you want to edit and the auth of the player you want to add: \n``!addplayer <team tag> <urt auth>``")
        return

    # Check if the tean exist
    cursor.execute("SELECT captain, name FROM Teams WHERE tag = %s;", (args[0],)) 
    team_toedit = cursor.fetchone()
    if not team_toedit:
        await message.author.send("This team does not exist.")
        return

    # Check if the user is the captain of the team
    if team_toedit[0] != str(message.author.id):
        await message.author.send("You are not the captain of that team.")
        return

    # Check if the auth is registered
    cursor.execute("SELECT ingame_name, discord_id FROM Users WHERE urt_auth = %s;", (args[1],))
    player_toadd = cursor.fetchone()
    if not player_toadd:
        await message.author.send("This auth is not registered yet, invite the player to join the discord server and use the ``!register`` command.")
        return

    # Add player to roster
    cursor.execute("INSERT INTO Roster(team_name, player_name) VALUES (%s, %s) ;", (team_toedit[1], player_toadd[0]))
    conn.commit()

    # DM invite to user
    player_topm = discord.utils.get(client.users, id=int(player_toadd[1]))
    await player_topm.send("coucou")


async def send_rooster_invite(message, player_topm):
    pass


#################EVENTS###################################

@client.event
async def on_message(message):
    #DM commands
    if message.guild == None and message.content.startswith('!addplayer'):
        await command_addplayer(message)
        return

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
    await client.change_presence(activity=discord.Game(name="Server Manager"))    

client.run(os.getenv('TOKEN'))

