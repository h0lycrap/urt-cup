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
import datetime
import re


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

    await user.send(alfred_quotes['cmdRegister_intro'])

    # Wait for team name and check if the team name is taken
    auth_checked = False
    while not auth_checked:
        await user.send(alfred_quotes['cmdRegister_prompt_auth'])
        auth_msg = await client.wait_for('message', check=check)
        auth = auth_msg.content.strip()

        # Check if auth is already registered
        cursor.execute("SELECT discord_id FROM Users WHERE urt_auth = %s", (auth,))   
        if cursor.fetchone():
            await user.send(alfred_quotes['cmdRegister_error_authalreadyreg'])
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

    # Update roster
    await update_roster()

async def command_editclan(message): 

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


    team_edition_finished = False
    while not team_edition_finished:
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
        if choice == '5':
            return
        
        # Ask if the user wants to keep going
        continue_message = await message.author.send(alfred_quotes['cmdEditClan_prompt_continue'])
        await continue_message.add_reaction(u"\U00002705")
        await continue_message.add_reaction(u"\U0000274C")

        def check_reaction(reaction, user):
            return user.id != client.user.id and reaction.message == continue_message and (str(reaction.emoji) == u"\U00002705" or str(reaction.emoji) == u"\U0000274C")

        reaction, _ = await client.wait_for('reaction_add', check=check_reaction)

        # Wants to continue
        if str(reaction.emoji) == u"\U00002705":
            continue

        # Is done
        elif str(reaction.emoji) == u"\U0000274C":
            await message.author.send(alfred_quotes['cmdEditClan_continue_no'])
            team_edition_finished = True


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
    def check_reaction(reaction, user):
            return user.id != client.user.id and reaction.message == invite_message and (str(reaction.emoji) == u"\U00002705" or str(reaction.emoji) == u"\U0000274C")
    reaction, _ = await client.wait_for('reaction_add', check=check_reaction)

    # Accepted invite
    if str(reaction.emoji) == u"\U00002705":
        cursor.execute("UPDATE Roster SET accepted=1 WHERE  team_tag = %s AND player_name=%s;", (team_toedit[1], player_toadd[0]))
        conn.commit()

        await captain.send(alfred_quotes['cmdAddPlayer_accepted_cap'].format(name=player_toadd[0], teamname=team_toedit[2]))

        # Show updated roster
        embed, _ = generate_team_embed(tag=team_toedit[1], show_invited=True)
        await captain.send(embed = embed)

        await player_topm.send(alfred_quotes['cmdAddPlayer_accepted'].format(teamname=team_toedit[2]))
        await update_roster()

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
    await update_roster()
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
    await update_roster();

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

    await update_roster()
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


# TODO Move this somwhere else
# Returns true if the input is a date DD/MM/YYYY and also returns the date object
def check_date_format(date_input): 
    date_elems = [e for e in date_input.split('/') if e.isnumeric()]
    if len(date_elems) != 3:
        return False, None

    day = int(date_elems[0])
    month = int(date_elems[1])
    year = int(date_elems[2])

    # Datetime checks the date validity (example: cant use 30/02)
    try:
        date = datetime.datetime(year, month, day)
        return True, date

    except ValueError:
        return False, None

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


async def command_createcup(message):
    def check(m):
        return m.author == message.author and m.channel == message.channel

    # Check permissions
    if not message.author.guild_permissions.manage_guild:
        await message.channel.send(alfred_quotes['cmdCreateCup_error_perm'])
        return

    # Wait for cup name
    await message.channel.send(alfred_quotes['cmdCreateCup_prompt_name'])
    name_msg = await client.wait_for('message', check=check)
    name = name_msg.content.strip()

    # Cancel 
    if name.lower() == '!cancel':
        await message.channel.send(alfred_quotes['cmdCreateCup_prompt_cancel'])
        return

    # Wait for number of teams and check validity
    number_of_teams_checked = False
    while not number_of_teams_checked:
        await message.channel.send(alfred_quotes['cmdCreateCup_prompt_nbofteams'])
        number_of_teams_msg = await client.wait_for('message', check=check)
        number_of_teams = number_of_teams_msg.content.lower().strip()

        if not number_of_teams.isnumeric():
            await message.channel.send(alfred_quotes['cmdCreateCup_error_nbofteams'])
        else:
            number_of_teams = int(number_of_teams)
            number_of_teams_checked = True


    # Wait for signup start date and check validity
    signup_start_date_checked = False
    while not signup_start_date_checked:
        await message.channel.send(alfred_quotes['cmdCreateCup_prompt_signupstart'])
        signupstart_msg = await client.wait_for('message', check=check)
        signupstart = signupstart_msg.content.lower().strip()

        # Cancel 
        if signupstart == '!cancel':
            await message.channel.send(alfred_quotes['cmdCreateCup_prompt_cancel'])
            return

        signup_start_date_checked, signup_start_date = check_date_format(signupstart)

        if not signup_start_date_checked:
            await message.channel.send(alfred_quotes['cmdCreateCup_error_date'])

    # Wait for signup end date and check validity
    signup_end_date_checked = False
    while not signup_end_date_checked:
        await message.channel.send(alfred_quotes['cmdCreateCup_prompt_signupend'])
        signupend_msg = await client.wait_for('message', check=check)
        signupend = signupend_msg.content.lower().strip()

        # Cancel 
        if signupend == '!cancel':
            await message.channel.send(alfred_quotes['cmdCreateCup_prompt_cancel'])
            return

        signup_end_date_checked, signup_end_date = check_date_format(signupend)

        if not signup_end_date_checked:
            await message.channel.send(alfred_quotes['cmdCreateCup_error_date'])
            continue

        # Check if the end date is after the start date
        if signup_start_date > signup_end_date:
            await message.channel.send(alfred_quotes['cmdCreateCup_error_startdate'])
            signup_end_date_checked = False
            continue

    cursor.execute("INSERT INTO Cups (name, number_of_teams, signup_start_date, signup_end_date) VALUES (%s, %d, %s, %s)", (name, number_of_teams, signup_start_date, signup_end_date))
    cup_id = cursor.lastrowid
    conn.commit()

    # Print log
    await message.channel.send(alfred_quotes['cmdCreateCup_success'])

    # Update signup message
    await update_signups()

async def command_signup(message):

    def check(m):
            return m.author == message.author and m.guild == None

    cursor.execute("SELECT id, name, number_of_teams, signup_start_date, signup_end_date FROM Cups;")
    cup_infos = cursor.fetchall()

    # List all cups open for signup
    # TODO: Maybe refactor this to use cup status
    cups_open =[]
    for cup_info in cup_infos:
        cup_id = cup_info[0]
        max_number_of_teams = cup_info[2]
        signup_start_date = datetime.datetime.strptime(cup_info[3], '%Y-%m-%d %H:%M:%S')
        signup_end_date = datetime.datetime.strptime(cup_info[4], '%Y-%m-%d %H:%M:%S')

        # Check if the signup are open
        if not(signup_start_date <= message.created_at <= signup_end_date):
            continue

        # Check if cup is full
        cursor.execute("SELECT team_tag FROM Signups WHERE cup_id=%d", (cup_id,))
        teams_signedup = cursor.fetchall()
        if len(teams_signedup) >= max_number_of_teams:
            continue

        cups_open.append(cup_info)


    # Print all cups available
    if len(cups_open) == 0:
        await message.author.send(alfred_quotes['cmdSignup_nocup'])
        return

    await message.author.send(alfred_quotes['cmdSignup_intro'])
    for (i, cup_open_info) in enumerate(cups_open):
        embed = generate_signup_embed(cup_open_info[0])
        await message.author.send(content=str(i+1), embed=embed)

    # Wait for choice and check validity
    choice_checked = False
    while not choice_checked:
        await message.author.send(alfred_quotes['cmdSignup_prompt_choice'])
        choice_msg = await client.wait_for('message', check=check)
        choice = choice_msg.content.strip()

        # Cancel 
        if choice.lower() == '!cancel':
            await message.author.send(alfred_quotes['cmdSignup_cancel'])
            return

        # Check if choice is a number and in the possible range
        if choice.isnumeric() and 1 <= int(choice) <= len(cups_open):
            choice_checked = True
        else:
            await message.author.send(alfred_quotes['cmdSignup_error_choice'])
    cup_choice = cups_open[int(choice)-1] 


     # Wait for clan tag and check if it exists
    tag_checked = False
    while not tag_checked:
        await message.author.send(alfred_quotes['cmdSignup_prompt_tag'].format(cupname=cup_choice[1]))
        tag_msg = await client.wait_for('message', check=check)
        tag = tag_msg.content.strip()
        tag_str = prevent_discord_formating(tag)

        # Cancel 
        if tag.lower() == '!cancel':
            await message.author.send(alfred_quotes['cmdSignup_cancel'])
            return

        # Check if the team exist
        cursor.execute("SELECT captain, tag, name, role_id, country FROM Teams WHERE tag = %s;", (tag,)) 
        team_toedit = cursor.fetchone()
        if not team_toedit:
            await message.author.send(alfred_quotes['cmdSignup_error_tagnotexist'])
            continue
            
        # Check if the user is the captain of the clan
        if team_toedit[0] != str(message.author.id):
            await message.author.send(alfred_quotes['cmdSignup_error_notcaptain'])
            continue

        tag_checked = True

    # Signup the clan and notify
    cursor.execute("INSERT INTO Signups (cup_id, team_tag) VALUES (%d, %s);", (cup_id, tag))
    conn.commit()
    await message.author.send(alfred_quotes['cmdSignup_success'].format(teamtag=tag_str, cupname=cup_choice[1]))

    # Update signups and log
    await update_signups()
    log_channel =  discord.utils.get(client.guilds[0].channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdSignup_log'].format(teamtag=tag_str, cupname=cup_choice[1]))

# TODO: move this somewhere else
def prevent_discord_formating(input_text):
    return input_text.replace('`', '\\`').replace('*', '\\*').replace('_', '\\_')

####################UPDATES#################################

async def update_roster():
    # Get channel
    roster_channel = discord.utils.get(client.guilds[0].channels, id=channel_roster_id) 

    # Delete index message if any
    roster_channel_messages = await roster_channel.history(limit=5).flatten()
    index_message = None
    for message in roster_channel_messages:
        if not message.embeds:
            continue
        if message.embeds[0].title.startswith(":pencil: Clan index"):
            index_message = message

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
            # Delete index message
            if index_message:
                await index_message.delete()
                index_message = None

            # Send new message and store message id
            new_roster_msg = await roster_channel.send(embed=embed)
            cursor.execute("UPDATE Teams SET roster_message_id=%s WHERE tag=%s", (str(new_roster_msg.id), team[0]))
            conn.commit()

    # Post or edit team index
    index_embed = await generate_team_index_embed()
    if index_message:
        await index_message.edit(embed=index_embed)
    else:
        await roster_channel.send(embed=index_embed)

async def update_signups():
    # Get channel (TODO:REFACTOR to account for new channels for different cups)
    signup_channel = discord.utils.get(client.guilds[0].channels, id=836895695269134386)

    # Get all cups
    cursor.execute("SELECT id, signup_message_id FROM Cups;")
    for cup_info in cursor.fetchall():

        # Generate the embed
        embed = generate_signup_embed(cup_info[0])

        # Check if there is a message id stored
        try:
            signup_message = await signup_channel.fetch_message(cup_info[1])
            await signup_message.edit(embed=embed)

        except:
            # Send new message and store message id
            new_signup_msg = await signup_channel.send(embed=embed)
            cursor.execute("UPDATE Cups SET signup_message_id=%s WHERE id=%s", (str(new_signup_msg.id), cup_info[0]))
            conn.commit()





##################EMBEDS####################################

def generate_team_embed(tag, show_invited=False):
    mini_number_players = 1

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

def generate_signup_embed(cup_id):
    # Get cup info
    cursor.execute("SELECT name, number_of_teams, signup_start_date, signup_end_date FROM Cups WHERE id=%d", (cup_id,))
    cup_info = cursor.fetchone()
    cup_name = cup_info[0]
    max_number_of_teams = cup_info[1]
    signup_start_date = datetime.datetime.strptime(cup_info[2], '%Y-%m-%d %H:%M:%S')
    signup_end_date = datetime.datetime.strptime(cup_info[3], '%Y-%m-%d %H:%M:%S')

    # Fetch signed up teams
    cursor.execute("SELECT team_tag FROM Signups WHERE cup_id=%d", (cup_id,))
    team_tags = cursor.fetchall()

    team_string = ""
    tag_string = ""

    #Create embed field content
    if team_tags:
        for i, team_tag in enumerate(team_tags):
            # Get team info
            cursor.execute("SELECT name, country FROM Teams WHERE tag=%s", (team_tag[0],))
            team_info = cursor.fetchone()
            team_name = team_info[0]
            team_flag = flag.flagize(team_info[1])
            team_tag_str = prevent_discord_formating(team_tag[0])
            index_str = str(i + 1) + "."

            team_string += f"``{index_str.ljust(3)}`` {team_flag} {team_name}\n"
            tag_string += f"{team_tag_str}\n"

        spots_available = max_number_of_teams - len(team_tags)
    else:
        spots_available = max_number_of_teams 

    # Fill empty spots
    for i in range(spots_available):
        index_str = str(i + len(team_tags) + 1) + "."
        team_string += f"``{index_str.ljust(3)}`` \u200b \u200b\u200b \u200b\u200b \u200b \u200b \u200b \u200b \u200b\n"
        tag_string += "\u200b \n"

    # Signup dates
    signup_string = f"__{signup_start_date.strftime('%a')} {signup_start_date.strftime('%b')} {signup_start_date.day}__ to __{signup_end_date.strftime('%a')} {signup_end_date.strftime('%b')} {signup_end_date.day}__"

    # Create the embed
    embed = discord.Embed(title=f":trophy: {cup_name}", color=0xFFD700, description="Open cup")
    embed.add_field(name="Team", value= team_string, inline=True)
    embed.add_field(name="Tag", value= tag_string, inline=True)
    embed.add_field(name="Signup dates", value= signup_string, inline=False)

    return embed

async def generate_team_index_embed():

    # Fetch teams with a message id not null
    cursor.execute("SELECT tag, country, roster_message_id FROM Teams WHERE roster_message_id != 'NULL'")
    teams = cursor.fetchall()

    # Sort the teams alphabetically on letters only
    sorted_teams = sorted(teams, key = lambda x: re.sub('[^A-Za-z]+', '', x[0]).lower())

    index_str_left = ""
    index_str_right = ""

    # Build embed content
    roster_channel = discord.utils.get(client.guilds[0].channels, id=channel_roster_id)
    for i, team_info in enumerate(sorted_teams):
        team_tag = flag.flagize(team_info[0])
        team_flag = flag.flagize(team_info[1])

        try:
            roster_message = await roster_channel.fetch_message(team_info[2])
        except:
            continue

        team_string = f"{team_flag} [{team_tag}]({roster_message.jump_url})\n"

        # Add to left or right column
        if i % 2 == 0:
            index_str_left += team_string
        else:
            index_str_right += team_string

    if len(index_str_right) == 0:
        index_str_right = "\u200b"
    if len(index_str_left) == 0:
        index_str_left = "\u200b"

    # Create the embed
    embed = discord.Embed(title=f":pencil: Clan index", color=0xFFD700, description="Click on a clan tag to jump to their roster")
    embed.add_field(name="Teams", value= index_str_left, inline=True)
    embed.add_field(name="\u200b", value= index_str_right, inline=True)

    return embed



#################EVENTS###################################

# Commands executable in dm only
dm_funcs = {'!editclan' : command_editclan, '!createclan' : command_createclan, '!signup' : command_signup}

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
    await update_roster()
    await update_signups()

client.run(os.getenv('TOKEN'))

