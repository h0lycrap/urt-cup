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
import asyncio


conn = mariadb.connect(
        user="dev",
        password=os.getenv('DBPASSWORD'),
        host=os.getenv('DBIP'),
        port=3306,
        database='urtcup'
    )
cursor = conn.cursor(dictionary=True)

intents = discord.Intents.all()
client = discord.Client(intents=intents)
guild = None

afred_quotes_loc = "data/alfred_quotes.json"
with open( afred_quotes_loc, 'rb' ) as json_alfred_quotes :
    alfred_quotes = json.load( json_alfred_quotes )

async_loop = asyncio.get_event_loop()

#number_emojis = [u"\U00000031\U0000FE0F\U000020E3", u"\U00000032\U0000FE0F\U000020E3", u"\U00000033\U0000FE0F\U000020E3", u"\U00000034\U0000FE0F\U000020E3", u"\U00000035\U0000FE0F\U000020E3", u"\U00000036\U0000FE0F\U000020E3", u"\U00000037\U0000FE0F\U000020E3", u"\U00000038\U0000FE0F\U000020E3", u"\U00000039\U0000FE0F\U000020E3", u"\U0001F51F"]
letter_emojis = [u"\U0001F1E6", u"\U0001F1E7", u"\U0001F1E8", u"\U0001F1E9", u"\U0001F1EA", u"\U0001F1EB", u"\U0001F1EC", u"\U0001F1ED", u"\U0001F1EE", u"\U0001F1EF", u"\U0001F1F0", u"\U0001F1F1", u"\U0001F1F2", u"\U0001F1F2", u"\U0001F1F3", u"\U0001F1F4", u"\U0001F1F5", u"\U0001F1F6", u"\U0001F1F7", u"\U0001F1F8", u"\U0001F1F9", u"\U0001F1FA", u"\U0001F1FB", u"\U0001F1FC", u"\U0001F1FD", u"\U0001F1FE", u"\U0001F1FF"]
number_emojis = []

role_unregistered_id = 836897738796826645
role_captains_id = 839893529517228113
role_flawless_crew_id = 839651903298207816
role_cup_supervisor_id = 836901156642226196
channel_log_id = 834947952023437403
channel_roster_id = 834931256918802512
message_welcome_id = 838861660805791825
category_match_schedule_id = 835237146225934426

max_players_per_team = 8

users_busy = []


###############COMMANDS########################################

async def command_zmb(message):
    zmb = discord.utils.get(guild.members, id=205821831964393472)
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

        if check_auth(auth):
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
    await user.remove_roles(discord.utils.get(guild.roles, id=role_unregistered_id))

    # Print on the log channel
    log_channel =  discord.utils.get(guild.channels, id=channel_log_id)
    embed = generate_player_embed(auth)
    await log_channel.send(content=alfred_quotes['cmdRegister_log'], embed=embed)

    # There can be permission errors if the user's role is higher in hierarchy than the bot
    try:
        await user.edit(nick=name)
    except Exception as e:
        pass

def check_auth(auth):
    login_search = requests.get(f"https://www.urbanterror.info/members/profile/{auth}/")
    if "No member with the login or id" in  login_search.text:
        return False
    else:
        return True



async def command_createclan(message):

    # Flag the user as busy
    users_busy.append(message.author.id)

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
    team_role = await guild.create_role(name=tag)

    # Add team to DB
    cursor.execute("INSERT INTO Teams(name, tag, country, captain, role_id) VALUES (%s, %s, %s, %s, %s) ;", (teamname, tag, country, message.author.id, team_role.id))
    conn.commit()

    # Add captain to team roster accepted=2 means captain
    captain = discord.utils.get(guild.members, id=int(message.author.id))
    captain_role = discord.utils.get(guild.roles, id=int(role_captains_id))
    await captain.add_roles(captain_role, team_role)
    cursor.execute("INSERT INTO Roster(team_tag, player_name, accepted) VALUES (%s, %s, %d) ;", (tag, captain.display_name, 2))
    conn.commit()

    await message.author.send(alfred_quotes['cmdCreateClan_success'])

    # Print on the log channel
    log_channel =  discord.utils.get(guild.channels, id=channel_log_id)
    embed, _ = generate_team_embed(tag)
    await log_channel.send(content=alfred_quotes['cmdCreateClan_log'], embed=embed)

    # Remove busy status
    users_busy.remove(message.author.id)

    # Update roster
    await update_roster()

async def command_editclan(message): 

    def check(m):
            return m.author == message.author and m.guild == None


    # List clans owned by the player
    cursor.execute("SELECT * FROM Teams WHERE captain = %s;", (str(message.author.id),))
    clans = cursor.fetchall()

    if not clans:
        await message.author.send(alfred_quotes['cmdEditClan_error_notcaptain'])
        return

    team_toedit = await generate_team_list_embed(clans,"Which clan do you want to edit?", message)



    team_edition_finished = False
    while not team_edition_finished:
        # Show team card and display choices
        embed, _ = generate_team_embed(tag=team_toedit['tag'], show_invited=True)
        await message.author.send(embed = embed)
        choice_message = await message.author.send(alfred_quotes['cmdEditClan_intro'])

        number_of_choices = 5
        applied_reaction_emojis = []
        for i in range(number_of_choices):
            await choice_message.add_reaction(number_emojis[i])
            applied_reaction_emojis.append(number_emojis[i].name)

        # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
        def check_reaction(reaction, user):
                return user.id != client.user.id and reaction.message == choice_message and reaction.emoji.name in applied_reaction_emojis
        reaction, _ = await client.wait_for('reaction_add', check=check_reaction)

        # Get the choice
        choice = applied_reaction_emojis.index(reaction.emoji.name) + 1


        # Commands available for team edits
        editclan_funcs = {1: add_player, 2: delete_player, 3: update_team_flag, 4: change_clan_captain, 5: delete_team}

        if choice in editclan_funcs:
            # Set busy status
            users_busy.append(message.author.id)

            await editclan_funcs[choice](team_toedit, message.author)

            # Remove busy status
            users_busy.remove(message.author.id)

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
            embed, _ = generate_team_embed(tag=team_toedit['tag'], show_invited=True)
            await message.author.send(content=alfred_quotes['cmdEditClan_continue_no'], embed=embed)
            team_edition_finished = True


# Check if the text is a valid flag emoji
def check_flag_emoji(flag_to_check):
    country = flag.dflagize(flag_to_check)
    cursor.execute("SELECT id FROM Countries WHERE id = %s;", (country,))
    return country, cursor.fetchone()
        

async def add_player(team_toedit, user):

    # Check if the max number of players per clan has been reached
    cursor.execute("SELECT * FROM Roster WHERE team_tag = %s;", (team_toedit['tag'],))
    players_inclan = cursor.fetchall()
    if len(players_inclan) >= max_players_per_team:
        await user.send(alfred_quotes['cmdAddPlayer_error_maxplayer'])
        return

    def check(m):
            return m.author == user and m.guild == None

    # Wait for the auth list to add
    await user.send(alfred_quotes['cmdAddPlayer_prompt_auth'])
    
    player_msg = await client.wait_for('message', check=check)
    auth_list = player_msg.content.strip().split(',')

    # Cancel 
    if player_msg.content.strip().lower() == '!cancel':
        await user.send(alfred_quotes['cmdAddPlayer_cancel'])
        return

    # Check if we are trying to add more players than the limit
    if len(auth_list) + len(players_inclan) > max_players_per_team:
        await user.send(alfred_quotes['cmdAddPlayer_error_maxplayer'])
        return

    for auth in auth_list:
        auth = auth.strip()

        # Check if the auth is registered
        cursor.execute("SELECT ingame_name, discord_id FROM Users WHERE urt_auth = %s;", (auth,))
        player_toadd = cursor.fetchone()
        if not player_toadd:
            await user.send(alfred_quotes['cmdAddPlayer_error_auth'].format(auth=auth))
            continue

        # Check if user was already invited
        cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toadd['ingame_name']))
        if cursor.fetchone():
            await user.send(alfred_quotes['cmdAddPlayer_error_alreadyinvited'].format(name=player_toadd['ingame_name']))
            continue

        # Add player to roster
        cursor.execute("INSERT INTO Roster(team_tag, player_name) VALUES (%s, %s) ;", (team_toedit['tag'], player_toadd['ingame_name']))
        conn.commit() 

        # Invite each player
        await user.send(alfred_quotes['cmdAddPlayer_invitesent'].format(name=player_toadd['ingame_name'])) 
        async_loop.create_task(invite_player(player_toadd, user, team_toedit))

async def invite_player(player_toadd, user, team_toedit):
    # DM invite to user
    player_topm = discord.utils.get(guild.members, id=int(player_toadd['discord_id']))
    captain = discord.utils.get(guild.members, id=int(user.id)) # Assuming the bot is only on 1 server

    invite_message = await player_topm.send(alfred_quotes['cmdAddPlayer_invite'].format(captain=captain.display_name, teamname=team_toedit['name']))
    await invite_message.add_reaction(u"\U00002705")
    await invite_message.add_reaction(u"\U0000274C") 

    # Print on the log channel
    log_channel =  discord.utils.get(guild.channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdAddPlayer_invite_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

    # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
    def check_reaction(reaction, user):
            return user.id != client.user.id and reaction.message == invite_message and (str(reaction.emoji) == u"\U00002705" or str(reaction.emoji) == u"\U0000274C")
    reaction, _ = await client.wait_for('reaction_add', check=check_reaction)

    # Check if the player was still invited
    cursor.execute("SELECT id FROM Roster WHERE accepted=0 AND team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toadd['ingame_name']))
    if not cursor.fetchone():
        await player_topm.send(alfred_quotes['cmdAddPlayer_nolongerinvited'].format(teamname=team_toedit['name']))
        return

    # Accepted invite
    if str(reaction.emoji) == u"\U00002705":
        cursor.execute("UPDATE Roster SET accepted=1 WHERE  team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toadd['ingame_name']))
        conn.commit()

        await captain.send(alfred_quotes['cmdAddPlayer_accepted_cap'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

        await player_topm.send(alfred_quotes['cmdAddPlayer_accepted'].format(teamname=team_toedit['name']))
        await update_roster()

        # Add team role to player
        team_role = discord.utils.get(guild.roles, id=int(team_toedit['role_id']))
        await player_topm.add_roles(team_role)

        # Print on the log channel
        await log_channel.send(alfred_quotes['cmdAddPlayer_accepted_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

    # Declined invite
    elif str(reaction.emoji) == u"\U0000274C":
        await captain.send(alfred_quotes['cmdAddPlayer_declined_cap'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))
        cursor.execute("DELETE FROM Roster WHERE  team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toadd['ingame_name']))
        conn.commit()
        await player_topm.send(alfred_quotes['cmdAddPlayer_declined'].format(teamname=team_toedit['name']))

        # Print on the log channel
        await log_channel.send(alfred_quotes['cmdAddPlayer_declined_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))


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
        if player_toremove['discord_id'] == str(user.id):
            await user.send(alfred_quotes['cmdDeletePlayer_error_self'])
            continue


        # Check if user is in clan
        cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toremove['ingame_name']))
        if not cursor.fetchone():
            await user.send(alfred_quotes['cmdDeletePlayer_error_notinclan'].format(name=player_toremove['ingame_name']))
            continue

        player_checked = True
    
    # Remove player from roster
    cursor.execute("DELETE FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toremove['ingame_name']))
    conn.commit()
    await user.send(alfred_quotes['cmdDeletePlayer_success'].format(name=player_toremove['ingame_name']))
    async_loop.create_task(update_roster())


    # Remove team role from player
    player_topm = discord.utils.get(guild.members, id=int(player_toremove['discord_id']))
    team_role = discord.utils.get(guild.roles, id=int(team_toedit['role_id']))
    await player_topm.remove_roles(team_role)

    # Notify removed user
    await player_topm.send(alfred_quotes['cmdDeletePlayer_success_dm'].format(teamname=team_toedit['name']))

    # Print on the log channel
    log_channel =  discord.utils.get(guild.channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdDeletePlayer_log'].format(name=player_toremove['ingame_name'], teamname=team_toedit['name']))


async def update_team_flag(team_toedit, user):
    def check(m):
            return m.author == user and m.guild == None

    # Wait for team flag and check if this is a flag emoji 
    oldflag = flag.flagize(team_toedit['country'])
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

    cursor.execute("UPDATE Teams SET country=%s WHERE tag=%s", (serialized_country, team_toedit['tag']))
    conn.commit()
    async_loop.create_task(update_roster());

    await user.send(alfred_quotes['cmdUpdateFlag_success'])

    # Print on the log channel
    log_channel =  discord.utils.get(guild.channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdUpdateFlag_log'].format(teamname=team_toedit['name'], oldflag=oldflag, newflag=country))

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
        cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], new_captain['ingame_name']))
        if not cursor.fetchone():
            await user.send(alfred_quotes['cmdChangeCaptain_error_notinclan'].format(name=new_captain['ingame_name']))
            continue

        player_checked = True
    
    # Change clan captain
    cursor.execute("UPDATE Roster SET accepted=2 WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], new_captain['ingame_name']))
    conn.commit()

    cursor.execute("UPDATE Teams SET captain=%s WHERE tag = %s ;", (new_captain['discord_id'], team_toedit['tag']))
    conn.commit()

    # Remove captain status from prev captain
    prev_captain = discord.utils.get(guild.members, id=int(user.id))
    cursor.execute("UPDATE Roster SET accepted=1 WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], prev_captain.display_name))
    conn.commit()

    async_loop.create_task(update_roster())
    await user.send(alfred_quotes['cmdChangeCaptain_success'].format(name=new_captain['ingame_name']))

    # Notify new captain
    player_topm = discord.utils.get(client.users, id=int(new_captain['discord_id']))
    await player_topm.send(alfred_quotes['cmdChangeCaptain_success_dm'].format(teamname=team_toedit['name']))

    # Print on the log channel
    log_channel =  discord.utils.get(guild.channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdChangeCaptain_log'].format(teamname=team_toedit['name'], oldcaptain=prev_captain.display_name, newcaptain=new_captain['ingame_name']))

async def delete_team(team_toedit, user):
    def check(m):
            return m.author == user and m.guild == None 

    # Wait for the choice 
    await user.send(alfred_quotes['cmdDeleteClan_intro'].format(teamname=team_toedit['name']))
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
            cursor.execute("SELECT roster_message_id FROM Teams WHERE tag = %s;", (team_toedit['tag'],))
            roster_message_id = cursor.fetchone()

            # Get channel and remove message
            roster_channel = discord.utils.get(guild.channels, id=channel_roster_id)
            try:
                roster_message = await roster_channel.fetch_message(roster_message_id['roster_message_id'])
                await roster_message.delete()
            except:
                pass

            # Delete team role
            try:
                team_role = discord.utils.get(guild.roles, id=int(team_toedit['role_id']))
                await team_role.delete()
            except Exception as e:
                print(e)

            # Delete clan
            cursor.execute("DELETE FROM Teams WHERE tag = %s;", (team_toedit['tag'],))
            conn.commit()

            # Delete from roster
            cursor.execute("DELETE FROM Roster WHERE team_tag = %s;", (team_toedit['tag'],))
            conn.commit()

            # Remove captain role if the captain is no longer captain of any team
            prev_captain = discord.utils.get(guild.members, id=int(user.id))
            captain_role = discord.utils.get(guild.roles, id=int(role_captains_id))
            cursor.execute("SELECT id FROM Roster WHERE accepted=2 AND player_name=%s", (prev_captain.display_name,))
            if not cursor.fetchone():
                await prev_captain.remove_roles(captain_role)

            # Notify
            await user.send(alfred_quotes['cmdDeleteClan_prompt_success'].format(teamname=team_toedit['name']))

            # Print on the log channel
            log_channel =  discord.utils.get(guild.channels, id=channel_log_id)
            await log_channel.send(alfred_quotes['cmdDeleteClan_log'].format(teamname=team_toedit['name']))

            # Update roster
            await update_roster()

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
        embed, _ = generate_team_embed(tag=team['tag'])

    elif player:
        embed = generate_player_embed(player['urt_auth'])

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

    cursor.execute("SELECT * FROM Cups;")
    cup_infos = cursor.fetchall()

    # List all cups open for signup
    # TODO: Maybe refactor this to use cup status
    cups_open =[]
    for cup_info in cup_infos:
        signup_start_date = datetime.datetime.strptime(cup_info['signup_start_date'], '%Y-%m-%d %H:%M:%S')
        signup_end_date = datetime.datetime.strptime(cup_info['signup_end_date'], '%Y-%m-%d %H:%M:%S')

        # Check if the signup are open
        if not(signup_start_date <= message.created_at <= signup_end_date):
            continue

        # Check if cup is full
        cursor.execute("SELECT team_tag FROM Signups WHERE cup_id=%d", (cup_info['id'],))
        teams_signedup = cursor.fetchall()
        if len(teams_signedup) >= cup_info['number_of_teams']:
            continue

        cups_open.append(cup_info)


    # Print all cups available
    if len(cups_open) == 0:
        await message.author.send(alfred_quotes['cmdSignup_nocup'])
        return

    await message.author.send(alfred_quotes['cmdSignup_intro'])
    for (i, cup_open_info) in enumerate(cups_open):
        embed = generate_signup_embed(cup_open_info['id'])
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
        await message.author.send(alfred_quotes['cmdSignup_prompt_tag'].format(cupname=cup_choice['name']))
        tag_msg = await client.wait_for('message', check=check)
        tag = tag_msg.content.strip()
        tag_str = prevent_discord_formating(tag)

        # Cancel 
        if tag.lower() == '!cancel':
            await message.author.send(alfred_quotes['cmdSignup_cancel'])
            return

        # Check if the team exist
        cursor.execute("SELECT * FROM Teams WHERE tag = %s;", (tag,)) 
        team_toedit = cursor.fetchone()
        if not team_toedit:
            await message.author.send(alfred_quotes['cmdSignup_error_tagnotexist'])
            continue
            
        # Check if the user is the captain of the clan
        if team_toedit['captain'] != str(message.author.id):
            await message.author.send(alfred_quotes['cmdSignup_error_notcaptain'])
            continue

        tag_checked = True

    # Signup the clan and notify
    cursor.execute("INSERT INTO Signups (cup_id, team_tag) VALUES (%d, %s);", (cup_choice['id'], tag))
    conn.commit()
    await message.author.send(alfred_quotes['cmdSignup_success'].format(teamtag=tag_str, cupname=cup_choice['name']))

    # Update signups and log
    await update_signups()
    log_channel =  discord.utils.get(guild.channels, id=channel_log_id)
    await log_channel.send(alfred_quotes['cmdSignup_log'].format(teamtag=tag_str, cupname=cup_choice['name']))

# TODO: move this somewhere else
def prevent_discord_formating(input_text):
    return input_text.replace('`', '\\`').replace('*', '\\*').replace('_', '\\_')


async def command_fixture(message):
    cursor.execute("SELECT * FROM Cups;")
    cups = cursor.fetchall()

    cup_name_list_str = ""
    for (i, cup_info) in enumerate(cups):
        index_str = (str(i + 1) + ".").ljust(2)
        cup_name_list_str += f"``{index_str}`` {cup_info['name']}\n"

    # Create cup list embed
    embed = discord.Embed(title=f"For which cup do you want to create the fixture?", color=0xFFD700)
    embed.add_field(name="Cup", value= cup_name_list_str, inline=True)
    cup_list_message = await message.channel.send(embed=embed)

    applied_reaction_emojis = []
    for i, cup_info in enumerate(cups):
        await cup_list_message.add_reaction(number_emojis[i])
        applied_reaction_emojis.append(number_emojis[i].name)

    # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
    def check_reaction(reaction, user):
            return user.id == message.author.id and reaction.message == cup_list_message and reaction.emoji.name in applied_reaction_emojis
    reaction, _ = await client.wait_for('reaction_add', check=check_reaction)

    # Get the choice
    cup_choice = applied_reaction_emojis.index(reaction.emoji.name)
    cup_toedit = cups[cup_choice]

    # List clans signed up in the cup
    cursor.execute("SELECT * FROM Signups WHERE cup_id = %s;", (cup_toedit['id'],))
    teams_signed_up  = cursor.fetchall()

    if not teams_signed_up:
        await message.channel.send("No team signed up for this cup")
        return

    # Get clan info list
    clan_info_list = []
    for team_signed_up in teams_signed_up:

        cursor.execute("SELECT * FROM Teams WHERE tag = %s;", (team_signed_up['team_tag'],))
        clan_info = cursor.fetchone()
        clan_info_list.append(clan_info)

    # First clan
    team1 = await generate_team_list_embed(clan_info_list, "First clan?", message)
    clan_info_list.remove(team1)

    # Second clan
    team2 = await generate_team_list_embed(clan_info_list, "Second clan?", message)

    # Select if BO1 or BO2 or BO3 or BO5 or BO7
    # TODO: maybe put this in a table in the DB
    formats = ['BO1', 'BO2', 'BO3', 'BO5']
    embed = discord.Embed(title=f"Match format?", color=0xFFD700)
    embed.add_field(name="Format", value= "``1.`` BO1 \n ``2.`` BO2 \n ``3.`` BO3 \n ``4.`` BO5", inline=True)
    fixture_format_message = await message.channel.send(embed=embed)

    applied_reaction_emojis = []
    for i in range(4):
        await fixture_format_message.add_reaction(number_emojis[i])
        applied_reaction_emojis.append(number_emojis[i].name)

    # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
    def check_reaction(reaction, user):
            return user.id == message.author.id and reaction.message == fixture_format_message and reaction.emoji.name in applied_reaction_emojis
    reaction, _ = await client.wait_for('reaction_add', check=check_reaction)

    # Get the choice
    format_choice = applied_reaction_emojis.index(reaction.emoji.name)
    fixture_format = formats[format_choice]


    # Get different roles that will have access to the channel
    role_team1 = discord.utils.get(guild.roles, id=int(team1['role_id'])) 
    role_team2 = discord.utils.get(guild.roles, id=int(team2['role_id'])) 
    role_flawless_crew = discord.utils.get(guild.roles, id=int(role_flawless_crew_id)) 
    role_cup_supervisor = discord.utils.get(guild.roles, id=int(role_cup_supervisor_id)) 

    # Set the permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        role_team1: discord.PermissionOverwrite(read_messages=True),
        role_team2: discord.PermissionOverwrite(read_messages=True),
        role_flawless_crew: discord.PermissionOverwrite(read_messages=True),
        role_cup_supervisor: discord.PermissionOverwrite(read_messages=True)
    }

    # Create text channel
    fixture_category = discord.utils.get(guild.channels, id=category_match_schedule_id) 
    fixture_channel = await guild.create_text_channel(f"abcd┋{team1['tag']} vs {team2['tag']}", overwrites=overwrites, category=fixture_category)

    # TODO: add this into DB

    # Send fixture card
    embed = generate_fixture_embed(team1, team2)
    fixture_card = await fixture_channel.send(embed=embed)

    """
    # Map 1
    cursor.execute("SELECT * FROM Maps;")
    map_list = sorted(cursor.fetchall(), key = lambda x: re.sub('[^A-Za-z]+', '', x['name']).lower())
    map1 = await generate_map_list_embed(map_list, "Map TS?", message)
    map_list.remove(map1)

    # Map2
    map2 = await generate_map_list_embed(map_list, "Map CTF?", message)

    embed = generate_fixture_embed(team1, team2, map1, map2)
    await message.channel.send(embed=embed)
    """

####################UPDATES#################################

async def update_roster():
    # Get channel
    roster_channel = discord.utils.get(guild.channels, id=channel_roster_id) 

    # Delete index message if any
    roster_channel_messages = await roster_channel.history(limit=5).flatten()
    index_message = None
    for message in roster_channel_messages:
        if not message.embeds:
            continue
        if message.embeds[0].title.startswith(":pencil: Clan index"):
            index_message = message

    cursor.execute("SELECT * FROM Teams;")
    for team in cursor.fetchall():  

        # Generate the embed
        embed, insuficient_roster = generate_team_embed(tag=team['tag'])

        if insuficient_roster:
            # Remove message from roster if there was one
            try:
                roster_message = await roster_channel.fetch_message(team['roster_message_id'])
                await roster_message.delete()
            except:
                pass
            continue

        # Check if there is a message id stored
        try:
            roster_message = await roster_channel.fetch_message(team['roster_message_id'])
            await roster_message.edit(embed=embed)
        except:
            # Delete index message
            if index_message:
                await index_message.delete()
                index_message = None

            # Send new message and store message id
            new_roster_msg = await roster_channel.send(embed=embed)
            cursor.execute("UPDATE Teams SET roster_message_id=%s WHERE tag=%s", (str(new_roster_msg.id), team['tag']))
            conn.commit()

    # Post or edit team index
    index_embed = await generate_team_index_embed()
    if index_message:
        await index_message.edit(embed=index_embed)
    else:
        await roster_channel.send(embed=index_embed)

async def update_signups():
    # Get channel (TODO:REFACTOR to account for new channels for different cups)
    signup_channel = discord.utils.get(guild.channels, id=836895695269134386)

    # Get all cups
    cursor.execute("SELECT id, signup_message_id FROM Cups;")
    for cup_info in cursor.fetchall():

        # Generate the embed
        embed = generate_signup_embed(cup_info['id'])

        # Check if there is a message id stored
        try:
            signup_message = await signup_channel.fetch_message(cup_info['signup_message_id'])
            await signup_message.edit(embed=embed)

        except:
            # Send new message and store message id
            new_signup_msg = await signup_channel.send(embed=embed)
            cursor.execute("UPDATE Cups SET signup_message_id=%s WHERE id=%s", (str(new_signup_msg.id), cup_info['id']))
            conn.commit()





##################EMBEDS####################################

async def generate_team_list_embed(clan_info_list, title, message):
    clans_string = ""
    tag_string = ""
    for (i, clan_info) in enumerate(clan_info_list):
        index_str = (str(i + 1) + ".").ljust(2)
        clan_flag = flag.flagize(clan_info['country'])
        clans_string += f"``{index_str}`` {clan_flag} {clan_info['name']}\n"
        tag_string += f"{clan_info['tag']}\n"

    # Create clan list embed
    embed = discord.Embed(title=title, color=0xFFD700)
    embed.add_field(name="Team", value= clans_string, inline=True)
    embed.add_field(name="Tag", value= tag_string, inline=True)

    # Check if DM or not
    if message.guild == None:
        clan_list_message = await message.author.send(embed=embed)
    else:
        clan_list_message = await message.channel.send(embed=embed)

    applied_reaction_emojis = []
    for i, clan_info in enumerate(clan_info_list):
        await clan_list_message.add_reaction(number_emojis[i])
        applied_reaction_emojis.append(number_emojis[i].name)

     # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
    def check_reaction(reaction, user):
            return user.id != client.user.id and reaction.message == clan_list_message and reaction.emoji.name in applied_reaction_emojis
    reaction, _ = await client.wait_for('reaction_add', check=check_reaction)

    # Get the choice
    clan_choice = clan_info_list[applied_reaction_emojis.index(reaction.emoji.name)]

    return clan_choice

async def generate_map_list_embed(map_list, title, message):
    maps_string = ""
    for (i, map_info) in enumerate(map_list):
        index_str = (str(i + 1) + ".").ljust(2)
        maps_string += f"``{index_str}`` {map_info['name']}\n"

    # Create clan list embed
    embed = discord.Embed(title=title, color=0xFFD700)
    embed.add_field(name="Map", value= maps_string, inline=True)

    # Check if DM or not
    if message.guild == None:
        map_list_message = await message.author.send(embed=embed)
    else:
        map_list_message = await message.channel.send(embed=embed)

    applied_reaction_emojis = []
    for i, map_info in enumerate(map_list):
        await map_list_message.add_reaction(number_emojis[i])
        applied_reaction_emojis.append(number_emojis[i].name)

     # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
    def check_reaction(reaction, user):
            return user.id != client.user.id and reaction.message == map_list_message and reaction.emoji.name in applied_reaction_emojis
    reaction, _ = await client.wait_for('reaction_add', check=check_reaction)

    # Get the choice
    map_choice = map_list[applied_reaction_emojis.index(reaction.emoji.name)]

    return map_choice


def generate_team_embed(tag, show_invited=False):
    mini_number_players = 1

    # Get the team info
    cursor.execute("SELECT * FROM Teams WHERE tag=%s;", (tag,))
    team = cursor.fetchone()
    country = flag.flagize(team['country'])
    captain = discord.utils.get(guild.members, id=int(team['captain']))
    name = team['name']

     # Get the players for each team
    cursor.execute("SELECT player_name, accepted FROM Roster WHERE team_tag = %s;", (tag,))
    players = cursor.fetchall()

    # Filter out unaccepted invites and check if there are the minimum number of players to display in the roster
    accepted_players = list(filter(lambda x: x['accepted'] != 0, players))

    # Get the list of invited players
    invited_players = list(filter(lambda x: x['accepted'] == 0, players))

    # Generate roster body
    roster_str1 = ""
    roster_str2 = "\u200b"
    roster_invited = ""
    for i, player in enumerate(accepted_players):

        # Get player country flag and urt auth
        cursor.execute("SELECT urt_auth, country FROM Users WHERE ingame_name = %s;", (player['player_name'],))
        player_info = cursor.fetchone()
        if not player_info:
            player_auth_str = "urtauth"
            player_flag_str = ":FR:"
        else:
            player_auth_str = player_info['urt_auth']
            player_flag_str = player_info['country']

        player_string = f"{flag.flagize(player_flag_str)} {player['player_name']} ``[{player_auth_str}]``\n"
        # Check if we add in the first column or the second one
        if i <= 3 or len(accepted_players) < mini_number_players:
            roster_str1 += player_string
        else:
            roster_str2 += player_string

    # Invited players loop
    for i, player in enumerate(invited_players):
        # Get player country flag and urt auth
        cursor.execute("SELECT urt_auth, country FROM Users WHERE ingame_name = %s;", (player['player_name'],))
        player_info = cursor.fetchone()
        if not player_info:
            player_auth_str = "urtauth"
            player_flag_str = ":FR:"
        else:
            player_auth_str = player_info['urt_auth']
            player_flag_str = player_info['country']

        roster_invited += f"{flag.flagize(player_flag_str)} {player['player_name']} ``[{player_auth_str}]``\n"

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
    cursor.execute("SELECT * FROM Users WHERE urt_auth=%s;", (auth,))
    player = cursor.fetchone()

    ds_player = discord.utils.get(guild.members, id=int(player['discord_id']))
    embed=discord.Embed(title=f"{flag.flagize(player['country'])} \u200b {player['ingame_name']}", color=0x9b2ab2)
    embed.add_field(name="Auth", value= player['urt_auth'], inline=False)
    embed.set_thumbnail(url=ds_player.avatar_url)

    # Get player's teams
    cursor.execute("SELECT team_tag, accepted FROM Roster WHERE player_name=%s", (player['ingame_name'],))
    teams = cursor.fetchall()

    # If the player is in no team
    if not teams:
        teams_str="."

    else:
        teams_str=""
        for team in teams:
            # Get team country
            cursor.execute("SELECT country FROM Teams WHERE tag=%s", (team['team_tag'],))
            country = cursor.fetchone()

            # If he is a member of the team
            if int(team['accepted']) == 1:
                teams_str += f"{flag.flagize(country['country'])} \u200b {team['team_tag']}\n"

            # If he is the captain of the team
            elif int(team['accepted']) == 2:
                teams_str += f"{flag.flagize(country['country'])} \u200b {team['team_tag']} (Captain)\n"

            # If he is inactive
            elif int(team['accepted']) == 3:
                teams_str += f"{flag.flagize(country['country'])} \u200b {team['team_tag']} (Inactive)\n" 

    embed.add_field(name="Clans", value= teams_str, inline=True)

    return embed

def generate_signup_embed(cup_id):
    # Get cup info
    cursor.execute("SELECT * FROM Cups WHERE id=%d", (cup_id,))
    cup_info = cursor.fetchone()
    cup_name = cup_info['name']
    max_number_of_teams = cup_info['number_of_teams']
    signup_start_date = datetime.datetime.strptime(cup_info['signup_start_date'], '%Y-%m-%d %H:%M:%S')
    signup_end_date = datetime.datetime.strptime(cup_info['signup_end_date'], '%Y-%m-%d %H:%M:%S')

    # Fetch signed up teams
    cursor.execute("SELECT team_tag FROM Signups WHERE cup_id=%d", (cup_id,))
    team_tags = cursor.fetchall()

    team_string = ""
    tag_string = ""

    #Create embed field content
    if team_tags:
        for i, team_tag in enumerate(team_tags):
            # Get team info
            cursor.execute("SELECT name, country FROM Teams WHERE tag=%s", (team_tag['team_tag'],))
            team_info = cursor.fetchone()
            team_name = team_info['name']
            team_flag = flag.flagize(team_info['country'])
            team_tag_str = prevent_discord_formating(team_tag['team_tag'])
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
    sorted_teams = sorted(teams, key = lambda x: re.sub('[^A-Za-z]+', '', x['tag']).lower())

    index_str_left = ""
    index_str_right = ""

    # Build embed content
    roster_channel = discord.utils.get(guild.channels, id=channel_roster_id)
    for i, team_info in enumerate(sorted_teams):
        team_tag = team_info['tag']
        team_flag = flag.flagize(team_info['country'])

        try:
            roster_message = await roster_channel.fetch_message(team_info['roster_message_id'])
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

def generate_fixture_embed(team1, team2):
    embed = discord.Embed(color=0xFFD700, title=f"{flag.flagize(team1['country'])} {team1['tag']} :black_small_square: vs :black_small_square: {team2['tag']} {flag.flagize(team2['country'])}", description= "Group stage game")
    embed.add_field(name=":pencil: Status", value= "-", inline=True)
    embed.add_field(name=":calendar_spiral: Date", value= "-", inline=True)
    embed.add_field(name=":alarm_clock: Time (CET)", value= "-", inline=True)
    embed.add_field(name=":map: Map TS", value= f"-", inline=True)
    embed.add_field(name=":map: Map CTF", value= f"-", inline=True)
    embed.add_field(name=":link: Demo and MOSS", value= f"https://dev.urt.li", inline=True)

    return embed

#################EVENTS###################################

# Commands executable in dm
dm_funcs = {'!editclan' : command_editclan, '!createclan' : command_createclan, '!signup' : command_signup, '!info' : command_info}

# Commands executable in channels
channel_funcs = {'!zmb' : command_zmb, '!lytchi' : command_lytchi ,'!st0mp' : command_st0mp, '!holy' : command_holycrap, '!urt5' : command_urt5, '!info' : command_info}

# Admin commands
admin_funcs = {'!createcup': command_createcup, '!fixture': command_fixture}

@client.event
async def on_message(message):
    msg_split = message.content.split(" ", 1)

    # Check if the author is the bot
    if message.author == client.user:
        return

    # DM and check if the user is busy
    if message.guild == None and msg_split[0] in dm_funcs and not (message.author.id in users_busy):
        await dm_funcs[msg_split[0]](message)
        return

    # Admin commands
    if message.guild != None and message.channel.id == channel_log_id and msg_split[0] in admin_funcs and not (message.author.id in users_busy):
        await admin_funcs[msg_split[0]](message)
        return
    
    # Channel commands
    if  message.guild != None and msg_split[0] in channel_funcs:
        await channel_funcs[msg_split[0]](message)
        return

@client.event
async def on_member_join(member):
    #Check if user is already registered and rename them if yes
    cursor.execute("SELECT ingame_name FROM Users WHERE discord_id = %s", (member.id,))   
    for name in cursor:
        await member.edit(nick=name['ingame_name'])
        return

    await member.add_roles(discord.utils.get(guild.roles, id=role_unregistered_id))

@client.event
async def on_raw_reaction_add(payload):
    if payload.message_id == message_welcome_id and str(payload.emoji) == '\U0001F440':

        # Check if user is already registered
        cursor.execute("SELECT urt_auth FROM Users WHERE discord_id = %s;", (payload.user_id,)) 
        if cursor.fetchone():
            return

        user = discord.utils.get(guild.members, id=payload.user_id)
        await register(user)



@client.event
async def on_ready():
    global guild

    print("Bot online")
    guild = client.guilds[0]
    print(guild.roles)

    for i in range(20):
        if i + 1 < 10:
            number_emojis.append(discord.utils.get(guild.emojis, name=str(i + 1 ) + "_"))
        else:
            number_emojis.append(discord.utils.get(guild.emojis, name=str(i + 1 )))

    await client.change_presence(activity=discord.Game(name="Server Manager")) 
    await update_roster()
    await update_signups()



client.run(os.getenv('TOKEN'))

