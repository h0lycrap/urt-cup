import discord
from dotenv import load_dotenv
load_dotenv()
import os
import mariadb
import logging
import flag
import random
import string
import requests
import json


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

afred_quotes_loc = "data/alfred_quotes.json"
with open( afred_quotes_loc, 'rb' ) as json_alfred_quotes :
    alfred_quotes = json.load( json_alfred_quotes )

role_unregistered_id = 836897738796826645
role_captains_id = 839893529517228113
channel_log_id = 834947952023437403
channel_roster_id = 834931256918802512
message_welcome_id = 838861660805791825

max_players_per_team = 12


###############COMMANDS########################################

async def command_zmb(message):
    zmb = discord.utils.get(client.guilds[0].members, id=205821831964393472)
    embed=discord.Embed(title=alfred_quotes['cmdZmb'], color=0x9b2ab2)
    embed.set_thumbnail(url=zmb.avatar_url)
    await message.channel.send(embed=embed) 

async def command_lytchi(message):
    await message.channel.send(alfred_quotes['cmdLytchi'])

async def command_st0mp(message):
    await message.channel.send(alfred_quotes['cmdSt0mp'])

async def command_holycrap(message):
    await message.channel.send(alfred_quotes['cmdHoly'])

async def command_urt5(message):
    await message.channel.send(alfred_quotes['cmdUrt5'])

async def register(user):
    def check(m):
            return m.author.id == user.id and m.guild == None

    await user.send(alfred_quotes['cmdRegister_Intro'])

    # Wait for team name and check if the team name is taken
    auth_checked = False
    while not auth_checked:
        await user.send(alfred_quotes['cmdRegister_prompt_auth'])
        auth_msg = await client.wait_for('message', check=check)
        auth = auth_msg.content.strip()

        # Check if auth is already registered
        cursor.execute("SELECT discord_id FROM Users WHERE urt_auth = %s", (auth,))   
        if cursor.fetchone():
            await user.send()
            continue
        
        if not auth.isalnum():
            await user.send(alfred_quotes['cmdRegister_error_invalidauth'])
            continue

        login_search = requests.get(f"https://www.urbanterror.info/members/profile/{auth}/")

        if "No member with the login or id" in  login_search.text:
            await user.send(alfred_quotes['cmdRegister_error_authdoesntexist'])
            continue

        auth_checked = True

    name_checked = False
    while not name_checked:
        await user.send(alfred_quotes['cmdRegister_prompt_name'])
        name_msg = await client.wait_for(
            'message', check=check)
        name = name_msg.content.strip()

        # Check if ingame name is already taken
        cursor.execute("SELECT discord_id FROM Users WHERE ingame_name = %s", (name,))   
        if cursor.fetchone():
            await user.send(alfred_quotes['cmdRegister_error_nametaken'])
        else:
            name_checked = True

    # Wait for flag and check if this is a flag emoji 
    country_checked = False
    while not country_checked:
        await user.send(alfred_quotes['cmdRegister_prompt_country'])
        country_msg = await client.wait_for('message', check=check)
        country, country_checked = check_flag_emoji(country_msg.content.strip())

        if not country_checked:
            await user.send(alfred_quotes['cmdRegister_error_country'])

    # Add user to DB and remove unregistered role
    cursor.execute("INSERT INTO Users(discord_id, urt_auth, ingame_name, country) VALUES (%s, %s, %s, %s) ;", (user.id, auth, name, country))
    conn.commit()
    await user.send(alfred_quotes['cmdRegister_success'])
    await user.remove_roles(discord.utils.get(client.guilds[0].roles, id=role_unregistered_id))

    # Print on the log channel
    log_channel =  discord.utils.get(client.guilds[0].channels, id=channel_log_id)
    embed = generate_player_embed(auth)
    await log_channel.send(content=alfred_quotes['cmdRegister_log'], embed=embed)

    # There can be permission errors if the user's role is higher in hierarchy than the bot
    try:
        await user.edit(nick=name)
    except Exception as e:
        pass


async def command_createclan(message):

    # Check command validity
    if len(message.content) > 11:
        if message.content[11] != " ":
            return

    def check(m):
            return m.author == message.author and m.guild == None

    await message.author.send(alfred_quotes['cmdCreateClan_intro'])

    # Wait for team name and check if the clan name is taken
    name_checked = False
    while not name_checked:
        await message.author.send(alfred_quotes['cmdCreateClan_prompt_name'])
        teamname_msg = await client.wait_for('message', check=check)
        teamname = teamname_msg.content.strip()

        # Cancel team creation
        if teamname.lower() == '!cancel':
            await message.author.send(alfred_quotes['cmdCreateClan_cancel'])
            return

        cursor.execute("SELECT id FROM Teams WHERE name = %s", (teamname,))   
        if cursor.fetchone():
            await message.author.send(alfred_quotes['cmdCreateClan_error_name'])
        else:
            name_checked = True


    # Wait for team tag and check if the team tag is taken    
    tag_checked = False
    while not tag_checked:
        await message.author.send(alfred_quotes['cmdCreateClan_prompt_tag'])
        tag_msg = await client.wait_for('message', check=check)
        tag = tag_msg.content.strip()

        # Cancel team creation
        if tag.lower() == '!cancel':
            await message.author.send(alfred_quotes['cmdCreateClan_cancel'])
            return

        cursor.execute("SELECT id FROM Teams WHERE tag = %s", (tag,))   
        if cursor.fetchone():
            await message.author.send(alfred_quotes['cmdCreateClan_error_tag'])
        else:
            tag_checked = True

    # Wait for team flag and check if this is a flag emoji 
    country_checked = False
    while not country_checked:
        await message.author.send(alfred_quotes['cmdCreateClan_prompt_flag'])
        country_msg = await client.wait_for('message', check=check)
        country, country_checked = check_flag_emoji(country_msg.content.strip())

        # Cancel team creation
        if country_msg.content.strip().lower() == '!cancel':
            await message.author.send(alfred_quotes['cmdCreateClan_cancel'])
            return

        if not country_checked:
            await message.author.send(alfred_quotes['cmdCreateClan_error_country'])

    # Create team ds role
    team_role = await client.guilds[0].create_role(name=tag)

    # Add team to DB
    cursor.execute("INSERT INTO Teams(name, tag, country, captain, role_id) VALUES (%s, %s, %s, %s, %s) ;", (teamname, tag, country, message.author.id, team_role.id))
    conn.commit()

    # Add captain to team roster accepted=2 means captain
    captain = discord.utils.get(client.guilds[0].members, id=int(message.author.id))
    captain_role = discord.utils.get(client.guilds[0].roles, id=int(role_captains_id))
    await captain.add_roles(captain_role, team_role)
    cursor.execute("INSERT INTO Roster(team_tag, player_name, accepted) VALUES (%s, %s, %d) ;", (tag, captain.display_name, 2))
    conn.commit()

    await message.author.send(alfred_quotes['cmdCreateClan_success'])

    # Print on the log channel
    log_channel =  discord.utils.get(client.guilds[0].channels, id=channel_log_id)
    embed, _ = generate_team_embed(tag)
    await log_channel.send(content=alfred_quotes['cmdCreateClan_log'], embed=embed)

async def command_editclan(message): 
    # Check command validity
    if len(message.content) > 10:
        if message.content[10] != " ":
            return

    def check(m):
            return m.author == message.author and m.guild == None

     # Wait for clan tag and check if it exists
    tag_checked = False
    while not tag_checked:
        await message.author.send(alfred_quotes['cmdEditClan_prompt_tag'])
        tag_msg = await client.wait_for('message', check=check)
        tag = tag_msg.content.strip()

        # Cancel 
        if tag.lower() == '!cancel':
            await message.author.send(alfred_quotes['cmdEditClan_cancel'])
            return

        # Check if the team exist
        cursor.execute("SELECT captain, tag, name, role_id, country FROM Teams WHERE tag = %s;", (tag,)) 
        team_toedit = cursor.fetchone()
        if not team_toedit:
            await message.author.send(alfred_quotes['cmdEditClan_error_tagnotexist'])
            continue
            
        # Check if the user is the captain of the clan
        if team_toedit[0] != str(message.author.id):
            await message.author.send(alfred_quotes['cmdEditClan_error_notcaptain'])
            continue

        tag_checked = True

    # Show team card and display choices
    embed, _ = generate_team_embed(tag=team_toedit[1], show_invited=True)
    await message.author.send(embed = embed)
    await message.author.send(alfred_quotes['cmdEditClan_intro'])
    option_checked = False

    # Wait for the choice 
    while not option_checked:
        await message.author.send(alfred_quotes['cmdEditClan_prompt_choice'])
        choice_msg = await client.wait_for('message', check=check)

        # Cancel 
        if choice_msg.content.lower().strip() == '!cancel':
            await message.author.send(alfred_quotes['cmdEditClan_cancel'])
            return

        # Check if the choice is valid
        choice = choice_msg.content.strip()
        if not choice.isnumeric() or not 1 <= int(choice) <= 5:
            await message.author.send(alfred_quotes['cmdEditClan_error_choice'])
        else:
            option_checked = True


    # Commands available for team edits
    editclan_funcs = {'1': add_player, '2': delete_player, '3': update_team_flag, '4': change_clan_captain, '5': delete_team}

    if choice in editclan_funcs:
        await editclan_funcs[choice](team_toedit, message.author)
        return


# Check if the text is a valid flag emoji
def check_flag_emoji(flag_to_check):
    country = flag.dflagize(flag_to_check)
    cursor.execute("SELECT id FROM Countries WHERE id = %s;", (country,))
    return country, cursor.fetchone()
        

async def add_player(team_toedit, user):

    # Check if the max number of players per clan has been reached
    cursor.execute("SELECT * FROM Roster WHERE team_tag = %s;", (team_toedit[1],))
    if len(cursor.fetchall()) >= max_players_per_team:
        await user.send(alfred_quotes['cmdAddPlayer_error_maxplayer'])
        return

    def check(m):
            return m.author == user and m.guild == None

    # Wait for the player auth, and check if it exist
    player_checked = False
    while not player_checked:
        await user.send(alfred_quotes['cmdAddPlayer_prompt_auth'])
        
        player_msg = await client.wait_for('message', check=check)
        auth = player_msg.content.strip()

        # Cancel 
        if auth.lower() == '!cancel':
            await user.send(alfred_quotes['cmdAddPlayer_cancel'])
            return

        # Check if the auth is registered
        cursor.execute("SELECT ingame_name, discord_id FROM Users WHERE urt_auth = %s;", (auth,))
        player_toadd = cursor.fetchone()
        if not player_toadd:
            await user.send(alfred_quotes['cmdAddPlayer_error_auth'].format(auth=auth))
            continue

        # Check if user was already invited
        cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit[1], player_toadd[0]))
        if cursor.fetchone():
            await user.send(alfred_quotes['cmdAddPlayer_error_alreadyinvited'].format(name=player_toadd[0]))
            continue

        player_checked = True

    # Add player to roster
    cursor.execute("INSERT INTO Roster(team_tag, player_name) VALUES (%s, %s) ;", (team_toedit[1], player_toadd[0]))
    conn.commit() 

    # DM invite to user
    player_topm = discord.utils.get(client.guilds[0].members, id=int(player_toadd[1]))
    captain = discord.utils.get(client.guilds[0].members, id=int(user.id)) # Assuming the bot is only on 1 server

    invite_message = await player_topm.send(alfred_quotes['cmdAddPlayer_invite'].format(captain=captain.display_name, teamname=team_toedit[2]))
    await invite_message.add_reaction(u"\U00002705")
    await invite_message.add_reaction(u"\U0000274C")

    await user.send(alfred_quotes['cmdAddPlayer_invitesent'].format(name=player_toadd[0]))  

    # Print on the log channel
    log_channel =  discord.utils.get(client.guilds[0].channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdAddPlayer_invite_log'].format(name=player_toadd[0], teamname=team_toedit[2]))


    # Show updated roster
    embed, _ = generate_team_embed(tag=team_toedit[1], show_invited=True)
    await user.send(embed = embed)

    # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
    def check(reaction, user):
            return user.id != client.user.id and reaction.message == invite_message and (str(reaction.emoji) == u"\U00002705" or str(reaction.emoji) == u"\U0000274C")
    reaction, _ = await client.wait_for('reaction_add', check=check)

    # Accepted invite
    if str(reaction.emoji) == u"\U00002705":
        cursor.execute("UPDATE Roster SET accepted=1 WHERE  team_tag = %s AND player_name=%s;", (team_toedit[1], player_toadd[0]))
        conn.commit()

        await captain.send(alfred_quotes['cmdAddPlayer_accepted_cap'].format(name=player_toadd[0], teamname=team_toedit[2]))

        # Show updated roster
        embed, _ = generate_team_embed(tag=team_toedit[1], show_invited=True)
        await captain.send(embed = embed)

        await player_topm.send(alfred_quotes['cmdAddPlayer_accepted'].format(teamname=team_toedit[2]))
        await UpdateRoster()

        # Add team role to player
        team_role = discord.utils.get(client.guilds[0].roles, id=int(team_toedit[3]))
        await player_topm.add_roles(team_role)

        # Print on the log channel
        await log_channel.send(alfred_quotes['cmdAddPlayer_accepted_log'].format(name=player_toadd[0], teamname=team_toedit[2]))

    # Declined invite
    elif str(reaction.emoji) == u"\U0000274C":
        await captain.send(alfred_quotes['cmdAddPlayer_declined_cap'].format(name=player_toadd[0], teamname=team_toedit[2]))
        cursor.execute("DELETE FROM Roster WHERE  team_tag = %s AND player_name=%s;", (team_toedit[1], player_toadd[0]))
        conn.commit()
        await player_topm.send(alfred_quotes['cmdAddPlayer_declined'].format(teamname=team_toedit[2]))

        # Print on the log channel
        await log_channel.send(alfred_quotes['cmdAddPlayer_declined_log'].format(name=player_toadd[0], teamname=team_toedit[2]))


async def delete_player(team_toedit, user):

    def check(m):
            return m.author == user and m.guild == None

    # Wait for the player auth, and check if it exist
    player_checked = False
    while not player_checked:
        await user.send(alfred_quotes['cmdDeletePlayer_prompt_auth'])
        
        player_msg = await client.wait_for('message', check=check)
        auth = player_msg.content.strip() 

        # Cancel 
        if auth.lower() == '!cancel':
            await user.send(alfred_quotes['cmdDeletePlayer_cancel'])
            return

        # Check if the auth is registered
        cursor.execute("SELECT ingame_name, discord_id FROM Users WHERE urt_auth = %s;", (auth,))
        player_toremove = cursor.fetchone()
        if not player_toremove:
            await user.send(alfred_quotes['cmdDeletePlayer_error_auth'].format(auth=auth))
            continue

        # Check if the user is trying to delete himself:
        if player_toremove[1] == str(user.id):
            await user.send(alfred_quotes['cmdDeletePlayer_error_self'])
            continue


        # Check if user is in clan
        cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit[1], player_toremove[0]))
        if not cursor.fetchone():
            await user.send(alfred_quotes['cmdDeletePlayer_error_notinclan'].format(name=player_toremove[0]))
            continue

        player_checked = True
    
    # Remove player from roster
    cursor.execute("DELETE FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit[1], player_toremove[0]))
    conn.commit()
    await UpdateRoster()
    await user.send(alfred_quotes['cmdDeletePlayer_success'].format(name=player_toremove[0]))

    # Show updated roster
    embed, _ = generate_team_embed(tag=team_toedit[1], show_invited=True)
    await user.send(embed = embed)


    # Remove team role from player
    player_topm = discord.utils.get(client.guilds[0].members, id=int(player_toremove[1]))
    team_role = discord.utils.get(client.guilds[0].roles, id=int(team_toedit[3]))
    await player_topm.remove_roles(team_role)

    # Notify removed user
    await player_topm.send(alfred_quotes['cmdDeletePlayer_success_dm'].format(teamname=team_toedit[2]))

    # Print on the log channel
    log_channel =  discord.utils.get(client.guilds[0].channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdDeletePlayer_log'].format(name=player_toremove[0], teamname=team_toedit[2]))


async def update_team_flag(team_toedit, user):
    def check(m):
            return m.author == user and m.guild == None

    # Wait for team flag and check if this is a flag emoji 
    oldflag = flag.flagize(team_toedit[4])
    country_checked = False
    while not country_checked:
        await user.send(alfred_quotes['cmdUpdateFlag_prompt_flag'])
        country_msg = await client.wait_for('message', check=check)
        country = country_msg.content.strip()
        serialized_country = flag.dflagize(country)

        # Cancel
        if country.lower() == '!cancel':
            await user.send(alfred_quotes['cmdUpdateFlag_cancel'])
            return

        cursor.execute("SELECT id FROM Countries WHERE id = %s;", (serialized_country,))
        if not cursor.fetchone():
            await user.send(alfred_quotes['cmdRegister_error_country'])
        else:
            country_checked = True

    cursor.execute("UPDATE Teams SET country=%s WHERE tag=%s", (serialized_country, team_toedit[1]))
    conn.commit()
    await UpdateRoster();

    await user.send(alfred_quotes['cmdUpdateFlag_success'])

    # Show updated roster
    embed, _ = generate_team_embed(tag=team_toedit[1], show_invited=True)
    await user.send(embed = embed)

    # Print on the log channel
    log_channel =  discord.utils.get(client.guilds[0].channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdUpdateFlag_log'].format(teamname=team_toedit[2], oldflag=oldflag, newflag=country))

async def change_clan_captain(team_toedit, user):

    def check(m):
            return m.author == user and m.guild == None

    # Wait for the player auth, and check if it exist
    player_checked = False
    while not player_checked:
        await user.send(alfred_quotes['cmdChangeCaptain_prompt_auth'])
        
        player_msg = await client.wait_for('message', check=check)
        auth = player_msg.content.strip()

        # Cancel 
        if auth.lower() == '!cancel':
            await user.send(alfred_quotes['cmdChangeCaptain_cancel'])
            return

        # Check if the auth is registered
        cursor.execute("SELECT ingame_name, discord_id FROM Users WHERE urt_auth = %s;", (auth,))
        new_captain = cursor.fetchone()
        if not new_captain:
            await user.send(alfred_quotes['cmdDeletePlayer_error_auth'].format(auth=auth))
            continue

        # Check if the user is trying to set captain to himself:
        if new_captain[1] == str(user.id):
            await user.send(alfred_quotes['cmdChangeCaptain_error_alreadycap'])
            continue

        # Check if user is in clan
        cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit[1], new_captain[0]))
        if not cursor.fetchone():
            await user.send(alfred_quotes['cmdChangeCaptain_error_notinclan'].format(name=new_captain[0]))
            continue

        player_checked = True
    
    # Change clan captain
    cursor.execute("UPDATE Roster SET accepted=2 WHERE team_tag = %s AND player_name=%s;", (team_toedit[1], new_captain[0]))
    conn.commit()

    cursor.execute("UPDATE Teams SET captain=%s WHERE tag = %s ;", (new_captain[1], team_toedit[1]))
    conn.commit()

    # Remove captain status from prev captain
    prev_captain = discord.utils.get(client.guilds[0].members, id=int(user.id))
    cursor.execute("UPDATE Roster SET accepted=1 WHERE team_tag = %s AND player_name=%s;", (team_toedit[1], prev_captain.display_name))
    conn.commit()

    await UpdateRoster()
    await user.send(alfred_quotes['cmdChangeCaptain_success'].format(name=new_captain[0]))

    # Show updated roster
    embed, _ = generate_team_embed(tag=team_toedit[1], show_invited=True)
    await user.send(embed = embed)

    # Notify new captain
    player_topm = discord.utils.get(client.users, id=int(new_captain[1]))
    await player_topm.send(alfred_quotes['cmdChangeCaptain_success_dm'].format(teamname=team_toedit[2]))

    # Print on the log channel
    log_channel =  discord.utils.get(client.guilds[0].channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdChangeCaptain_log'].format(teamname=team_toedit[2], oldcaptain=prev_captain.display_name, newcaptain=new_captain[0]))

async def delete_team(team_toedit, user):
    def check(m):
            return m.author == user and m.guild == None 

    # Wait for the choice 
    await user.send(alfred_quotes['cmdDeleteClan_intro'].format(teamname=team_toedit[2]))
    option_checked = False
    while not option_checked:
        await user.send(alfred_quotes['cmdDeleteClan_prompt_choice'])
        choice_msg = await client.wait_for('message', check=check)
        choice = choice_msg.content.lower().strip()

        # Cancel 
        if choice == '!cancel':
            await user.send(alfred_quotes['cmdDeleteClan_prompt_cancel'])
            return

        # Cancel
        if choice == 'no':
            await user.send(alfred_quotes['cmdDeleteClan_prompt_cancel'])
            return
        
        if choice == 'yes':
            # Remove roster message
            cursor.execute("SELECT roster_message_id FROM Teams WHERE tag = %s;", (team_toedit[1],))
            roster_message_id = cursor.fetchone()

            # Get channel and remove message
            roster_channel = discord.utils.get(client.guilds[0].channels, id=channel_roster_id)
            try:
                roster_message = await roster_channel.fetch_message(roster_message_id[0])
                await roster_message.delete()
            except:
                pass

            # Delete team role
            try:
                team_role = discord.utils.get(client.guilds[0].roles, id=int(team_toedit[3]))
                await team_role.delete()
            except Exception as e:
                print(e)

            # Delete clan
            cursor.execute("DELETE FROM Teams WHERE tag = %s;", (team_toedit[1],))
            conn.commit()

            # Delete from roster
            cursor.execute("DELETE FROM Roster WHERE team_tag = %s;", (team_toedit[1],))
            conn.commit()

            # Remove captain role if the captain is no longer captain of any team
            prev_captain = discord.utils.get(client.guilds[0].members, id=int(user.id))
            captain_role = discord.utils.get(client.guilds[0].roles, id=int(role_captains_id))
            cursor.execute("SELECT id FROM Roster WHERE accepted=2 AND player_name=%s", (prev_captain.display_name,))
            if not cursor.fetchone():
                await prev_captain.remove_roles(captain_role)

            # Notify
            await user.send(alfred_quotes['cmdDeleteClan_prompt_success'].format(teamname=team_toedit[2]))

            # Print on the log channel
            log_channel =  discord.utils.get(client.guilds[0].channels, id=channel_log_id)
            await log_channel.send(alfred_quotes['cmdDeleteClan_log'].format(teamname=team_toedit[2]))

            return


def generate_team_embed(tag, show_invited=False):
    mini_number_players = 5

    # Get the team info
    cursor.execute("SELECT country, captain, name FROM Teams WHERE tag=%s;", (tag,))
    team = cursor.fetchone()
    country = flag.flagize(team[0])
    captain = discord.utils.get(client.guilds[0].members, id=int(team[1]))
    name = team[2]

     # Get the players for each team
    cursor.execute("SELECT player_name, accepted FROM Roster WHERE team_tag = %s;", (tag,))
    players = cursor.fetchall()

    # Filter out unaccepted invites and check if there are the minimum number of players to display in the roster
    accepted_players = list(filter(lambda x: x[1] != 0, players))

    # Get the list of invited players
    invited_players = list(filter(lambda x: x[1] == 0, players))

    # Generate roster body
    roster_str1 = ""
    roster_str2 = "\u200b"
    roster_invited = ""
    for i, player in enumerate(accepted_players):

        # Get player country flag and urt auth
        cursor.execute("SELECT urt_auth, country FROM Users WHERE ingame_name = %s;", (player[0],))
        player_info = cursor.fetchone()
        if not player_info:
            player_auth_str = "urtauth"
            player_flag_str = ":FR:"
        else:
            player_auth_str = player_info[0]
            player_flag_str = player_info[1]

        player_string = f"{flag.flagize(player_flag_str)} {player[0]} ``[{player_auth_str}]``\n"
        # Check if we add in the first column or the second one
        if i <= 3 or len(accepted_players) < mini_number_players:
            roster_str1 += player_string
        else:
            roster_str2 += player_string

    # Invited players loop
    for i, player in enumerate(invited_players):
        # Get player country flag and urt auth
        cursor.execute("SELECT urt_auth, country FROM Users WHERE ingame_name = %s;", (player[0],))
        player_info = cursor.fetchone()
        if not player_info:
            player_auth_str = "urtauth"
            player_flag_str = ":FR:"
        else:
            player_auth_str = player_info[0]
            player_flag_str = player_info[1]

        roster_invited += f"{flag.flagize(player_flag_str)} {player[0]} ``[{player_auth_str}]``\n"

    # Create embed
    embed=discord.Embed(title=f"{name} {country}", color=13695009)
    embed.add_field(name=f"**Captain: **{captain.display_name}     |     **Tag: **{tag}", value= "\u200b", inline=False)
    embed.add_field(name="Members [auth] ", value= roster_str1, inline=True)
    embed.add_field(name="\u200b", value=roster_str2, inline=True)
    if show_invited and roster_invited != "":
        embed.add_field(name="Invited", value=roster_invited, inline=False)
    embed.add_field(name="Inactives", value=".", inline=False)
    embed.add_field(name="Discord", value="https://discord.gg/HzkvFEs", inline=True) # Hardcoded for now
    embed.add_field(name="Awards", value=":first_place: :second_place: :third_place:", inline=True) # Hardcoded for now

    return embed, len(accepted_players) < mini_number_players

def generate_player_embed(auth):
    cursor.execute("SELECT discord_id, urt_auth, ingame_name, country FROM Users WHERE urt_auth=%s;", (auth,))
    player = cursor.fetchone()

    ds_player = discord.utils.get(client.guilds[0].members, id=int(player[0]))
    embed=discord.Embed(title=f"{flag.flagize(player[3])} \u200b {player[2]}", color=0x9b2ab2)
    embed.add_field(name="Auth", value= player[1], inline=False)
    embed.set_thumbnail(url=ds_player.avatar_url)

    # Get player's teams
    cursor.execute("SELECT team_tag, accepted FROM Roster WHERE player_name=%s", (player[2],))
    teams = cursor.fetchall()

    # If the player is in no team
    if not teams:
        teams_str="."

    else:
        teams_str=""
        for team in teams:
            # Get team country
            cursor.execute("SELECT country FROM Teams WHERE tag=%s", (team[0],))
            country = cursor.fetchone()

            # If he is a member of the team
            if int(team[1]) == 1:
                teams_str += f"{flag.flagize(country[0])} \u200b {team[0]}\n"

            # If he is the captain of the team
            elif int(team[1]) == 2:
                teams_str += f"{flag.flagize(country[0])} \u200b {team[0]} (Captain)\n"

            # If he is inactive
            elif int(team[1]) == 3:
                teams_str += f"{flag.flagize(country[0])} \u200b {team[0]} (Inactive)\n" 

    embed.add_field(name="Clans", value= teams_str, inline=True)

    return embed

async def UpdateRoster():
    # Get channel
    roster_channel = discord.utils.get(client.guilds[0].channels, id=channel_roster_id) # Assuming the bot is on 1 server only

    cursor.execute("SELECT tag, country, captain, roster_message_id, name FROM Teams;")
    for team in cursor.fetchall():  

        # Generate the embed
        embed, insuficient_roster = generate_team_embed(tag=team[0])

        if insuficient_roster:
            # Remove message from roster if there was one
            try:
                roster_message = await roster_channel.fetch_message(team[3])
                await roster_message.delete()
            except:
                pass
            continue

        # Check if there is a message id stored
        try:
            roster_message = await roster_channel.fetch_message(team[3])
            await roster_message.edit(embed=embed)
        except:

            # Send new message and store message id
            new_roster_msg = await roster_channel.send(embed=embed)
            cursor.execute("UPDATE Teams SET roster_message_id=%s WHERE tag=%s", (str(new_roster_msg.id), team[0]))
            conn.commit()

async def command_createcup(message):
    # Check args
    args = message.content[len("!createcup"):].split()
    if len(args) != 2 or not args[1].isnumeric():
        await message.channel.send(alfred_quotes['cmdCreateCup_error_args'])
        return

    # TODO Use embed instead
    signup_msg_content_title = "                     :small_orange_diamond: **Signup List** :small_orange_diamond:\n\n"
    signup_msg_content = "~\n" + signup_msg_content_title
    signup_msg_content += "  __N__                        __Teams__                        __Tag__\n\n"
    for i in range(1, int(args[1])+1):
        index_string = str(i) + "."
        signup_msg_content += f"``{index_string.ljust(3)}``  :black_small_square: :flag_white: ``            `` :black_small_square: ``       ``\n\n"

    # TODO: Refactor the signup channel identification 
    signup_channel = discord.utils.get(client.guilds[0].channels, id=836895695269134386)
    signup_msg = await signup_channel.send(signup_msg_content)

async def command_info(message):
    # Check command validity
    if len(message.content) > len("!info") and message.content[len("!info")] != " ":
        return

    # Check args
    args = message.content[len("!info"):].split()
    if len(args) != 1:
        if message.guild == None:
            await message.author.send(alfred_quotes['cmdInfo_error_args'])
            return
        await message.channel.send(alfred_quotes['cmdInfo_error_args'])
        return

    # Check if this is a mention and extract user id
    if args[0].startswith("<@!") and args[0].endswith(">"):
        args[0] = args[0][3:-1] 

    cursor.execute("SELECT tag, country, captain, roster_message_id, name FROM Teams WHERE tag=%s;", (args[0],))
    team = cursor.fetchone()

    cursor.execute("SELECT discord_id, urt_auth, ingame_name, country FROM Users WHERE discord_id=%s OR urt_auth=%s OR ingame_name=%s;", (args[0], args[0], args[0]))
    player = cursor.fetchone()

    if not team and not player:
        if message.guild == None:
            await message.author.send(alfred_quotes['cmdInfo_error_doesntexist'])
            return
        await message.channel.send(alfred_quotes['cmdInfo_error_doesntexist'])
        return

    if team:
        embed, _ = generate_team_embed(tag=team[0])

    elif player:
        embed = generate_player_embed(player[1])

    # Send to author if this was in dm 
    if message.guild == None:
        await message.author.send(embed=embed)
        return

    await message.channel.send(embed=embed)





#################EVENTS###################################

# Commands executable in dm only
dm_funcs = {'!editclan' : command_editclan, '!createclan' : command_createclan}

# Commands executable both in dm and channels
dm_channel_funcs = {'!info' : command_info}

# Commands executable in channels only
channel_funcs = {'!zmb' : command_zmb, '!lytchi' : command_lytchi ,'!st0mp' : command_st0mp, '!holy' : command_holycrap, '!urt5' : command_urt5, '!createcup': command_createcup}

@client.event
async def on_message(message):
    msg_split = message.content.split(" ", 1)

    if message.guild == None and msg_split[0] in dm_funcs:
        await dm_funcs[msg_split[0]](message)
        return

    if  msg_split[0] in dm_channel_funcs:
        await dm_channel_funcs[msg_split[0]](message)
        return
    
    #Check if the message is a dm or if the author is the bot
    if message.guild == None or message.author == client.user:
        return

    if  msg_split[0] in channel_funcs:
        await channel_funcs[msg_split[0]](message)
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
async def on_raw_reaction_add(payload):
    if payload.message_id == message_welcome_id and str(payload.emoji) == '\U0001F440':

        # Check if user is already registered
        cursor.execute("SELECT urt_auth FROM Users WHERE discord_id = %s;", (payload.user_id,)) 
        if cursor.fetchone():
            return

        user = discord.utils.get(client.guilds[0].members, id=payload.user_id)
        await register(user)



@client.event
async def on_ready():
    print("Bot online")
    await client.change_presence(activity=discord.Game(name="Server Manager")) 
    await UpdateRoster()

client.run(os.getenv('TOKEN'))

