import discord
import flag
import re
import datetime
import cogs.common.utils as utils

def player(bot, auth):
    bot.cursor.execute("SELECT * FROM Users WHERE urt_auth=%s;", (auth,))
    player = bot.cursor.fetchone()

    ds_player = discord.utils.get(bot.guilds[0].members, id=int(player['discord_id']))
    embed=discord.Embed(title=f"{flag.flagize(player['country'])} \u200b {player['ingame_name']}", color=0x9b2ab2)
    embed.add_field(name="Auth", value= player['urt_auth'], inline=False)
    embed.set_thumbnail(url=ds_player.avatar_url)

    # Get player's teams
    bot.cursor.execute("SELECT team_id, accepted FROM Roster WHERE player_id=%s", (player['id'],))
    teams = bot.cursor.fetchall()

    # If the player is in no team
    if not teams:
        teams_str="."

    else:
        teams_str=""
        for team in teams:
            # Get team country
            bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (team['team_id'],))
            team_info = bot.cursor.fetchone()

            # If he is a member of the team
            if int(team['accepted']) == 1:
                teams_str += f"{flag.flagize(team_info['country'])} \u200b {utils.prevent_discord_formating(team_info['tag'])}\n"

            # If he is the captain of the team
            elif int(team['accepted']) == 2:
                teams_str += f"{flag.flagize(team_info['country'])} \u200b {utils.prevent_discord_formating(team_info['tag'])} (Captain)\n"

            # If he is inactive
            elif int(team['accepted']) == 3:
                teams_str += f"{flag.flagize(team_info['country'])} \u200b {utils.prevent_discord_formating(team_info['tag'])} (Inactive)\n" 

    embed.add_field(name="Clans", value= teams_str, inline=True)

    return embed

def team(bot, tag, show_invited=False): 
    mini_number_players = 1

    # Get the team info
    bot.cursor.execute("SELECT * FROM Teams WHERE tag=%s;", (tag,))
    team = bot.cursor.fetchone()
    country = flag.flagize(team['country'])
    #captain = discord.utils.get(bot.guilds[0].members, id=int(team['captain']))
    name = team['name']
    discord_link = team['discord_link']

    # Get captain info
    bot.cursor.execute("SELECT * FROM Users WHERE id=%s", (team['captain'],))
    captain = bot.cursor.fetchone()

     # Get the players for each team
    bot.cursor.execute("SELECT player_id, accepted FROM Roster WHERE team_id = %s;", (team['id'],))
    players = bot.cursor.fetchall()

    # Filter out unaccepted invites and check if there are the minimum number of players to display in the roster
    accepted_players = list(filter(lambda x: x['accepted'] != 0, players))

    # Get the members 
    members = list(filter(lambda x: x['accepted'] == 1 or x['accepted'] == 2, accepted_players))

    # Get the inactives 
    inactives= list(filter(lambda x: x['accepted'] == 3, accepted_players))

    # Get inactive name list
    if len(inactives) == 0:
        inactive_string = "None"
    else:
        inactive_string = ""
        for inactive in inactives[:-1]:

            # Get inactive info
            bot.cursor.execute("SELECT * FROM Users Where id=%s", (inactive['player_id'],))
            inactive_info = bot.cursor.fetchone()
            inactive_string += f"{flag.flagize(inactive_info['country'])} {inactive_info['ingame_name']}, "

        bot.cursor.execute("SELECT * FROM Users Where id=%s", (inactives[-1]['player_id'],))
        inactive_info = bot.cursor.fetchone()
        inactive_string += f"{flag.flagize(inactive_info['country'])} {inactive_info['ingame_name']}"


    # Get the list of invited players
    invited_players = list(filter(lambda x: x['accepted'] == 0, players))

    # Generate roster body
    roster_str1 = ""
    roster_str2 = "\u200b"
    roster_invited = ""
    for i, player in enumerate(members):

        # Get player country flag and urt auth
        bot.cursor.execute("SELECT * FROM Users WHERE id = %s;", (player['player_id'],))
        player_info = bot.cursor.fetchone()
        if not player_info:
            player_auth_str = "urtauth"
            player_flag_str = ":FR:"
        else:
            player_auth_str = player_info['urt_auth']
            player_flag_str = player_info['country']

        player_string = f"{flag.flagize(player_flag_str)} {player_info['ingame_name']} ``[{player_auth_str}]``\n"
        # Check if we add in the first column or the second one
        if i % 2 == 0:
            roster_str1 += player_string
        else:
            roster_str2 += player_string

    # Invited players loop
    for i, player in enumerate(invited_players):
        # Get player country flag and urt auth
        bot.cursor.execute("SELECT * FROM Users WHERE id = %s;", (player['player_id'],))
        player_info = bot.cursor.fetchone()
        if not player_info:
            player_auth_str = "urtauth"
            player_flag_str = ":FR:"
        else:
            player_auth_str = player_info['urt_auth']
            player_flag_str = player_info['country']

        roster_invited += f"{flag.flagize(player_flag_str)} {player_info['ingame_name']} ``[{player_auth_str}]``\n"

    # Create embed
    embed=discord.Embed(title=f"{utils.prevent_discord_formating(name)} {country}", color=13695009)
    embed.add_field(name=f"**Captain: **{captain['ingame_name']}     |     **Tag: **{utils.prevent_discord_formating(tag)}", value= "\u200b", inline=False)
    embed.add_field(name="Members [auth] ", value= roster_str1, inline=True)
    embed.add_field(name="\u200b", value=roster_str2, inline=True)
    if show_invited and roster_invited != "":
        embed.add_field(name="Invited", value=roster_invited, inline=False)
    embed.add_field(name="Inactives", value=inactive_string, inline=False)
    embed.add_field(name="Discord", value=discord_link, inline=True)
    embed.add_field(name="Awards", value="None", inline=True) # Hardcoded for now

    return embed, len(accepted_players) < mini_number_players


async def team_index(bot):

    # Fetch teams with a message id not null
    bot.cursor.execute("SELECT tag, country, roster_message_id FROM Teams WHERE roster_message_id != 'NULL'")
    teams = bot.cursor.fetchall()

    # Sort the teams alphabetically on letters only
    sorted_teams = sorted(teams, key = lambda x: re.sub('[^A-Za-z]+', '', x['tag']).lower())

    index_str_left = ""
    index_str_right = ""

    # Build embed content
    roster_channel = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_id)
    for i, team_info in enumerate(sorted_teams):
        team_tag = team_info['tag']
        team_flag = flag.flagize(team_info['country'])

        try:
            roster_message = await roster_channel.fetch_message(team_info['roster_message_id'])
        except:
            continue

        team_string = f"{team_flag} [{utils.prevent_discord_formating(team_tag)}]({roster_message.jump_url})\n"

        # Add to left or right column
        if i % 2 == 0:
            index_str_left += team_string
        else:
            index_str_right += team_string

    if len(index_str_right) == 0:
        index_str_right = "\u200b"
    if len(index_str_left) == 0:
        index_str_left = "\u200b"

    # Get total number of players in teams
    bot.cursor.execute("SELECT * FROM Roster")
    total_players = bot.cursor.fetchall()

    # Create the embed
    embed = discord.Embed(title=f":pencil: Clan index", color=0xFFD700, description="Click on a clan tag to jump to their roster")
    embed.add_field(name="Teams", value= index_str_left, inline=True)
    embed.add_field(name="\u200b", value= index_str_right, inline=True)
    embed.set_footer(text=f"Total: {len(sorted_teams)} Teams, {len(total_players)} Players")

    return embed


async def team_list(bot, clan_info_list, title, message): # TODO refactor this into a drop list
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
        await clan_list_message.add_reaction(bot.number_emojis[i])
        applied_reaction_emojis.append(bot.number_emojis[i].name)

     # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
    def check_reaction(reaction, user):
            return user.id != bot.user.id and reaction.message == clan_list_message and reaction.emoji.name in applied_reaction_emojis
    reaction, _ = await bot.wait_for('reaction_add', check=check_reaction)

    # Get the choice
    clan_choice = clan_info_list[applied_reaction_emojis.index(reaction.emoji.name)]

    return clan_choice

async def signup(bot, cup_id):
    # Get cup info
    bot.cursor.execute("SELECT * FROM Cups WHERE id=%d", (cup_id,))
    cup_info = bot.cursor.fetchone()
    cup_name = cup_info['name']
    signup_start_date = datetime.datetime.strptime(cup_info['signup_start_date'], '%Y-%m-%d %H:%M:%S')
    signup_end_date = datetime.datetime.strptime(cup_info['signup_end_date'], '%Y-%m-%d %H:%M:%S')

    # Fetch signed up teams
    bot.cursor.execute("SELECT team_id FROM Signups WHERE cup_id=%d", (cup_id,))
    team_ids = bot.cursor.fetchall()

    team_string = ""
    tag_string = ""

    roster_channel = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_id)

    #Create embed field content
    if team_ids:
        for i, team_id in enumerate(team_ids):
            # Get team info
            bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (team_id['team_id'],))
            team_info = bot.cursor.fetchone()
            team_name = utils.prevent_discord_formating(team_info['name'])
            team_flag = flag.flagize(team_info['country'])
            team_tag_str = utils.prevent_discord_formating(team_info['tag'])
            index_str = str(i + 1) + "."

            # Get roster link
            roster_message = await roster_channel.fetch_message(team_info['roster_message_id'])
            roster_link = roster_message.jump_url

            team_string += f"{team_flag} {team_name}\n"
            tag_string += f"{team_tag_str}\n"

            

        
    else:
        team_string = "No team signed up yet" 
        tag_string = "\u200b"

    # Fill empty spots
    #for i in range(spots_available):
    #    index_str = str(i + len(team_ids) + 1) + "."
    #    team_string += f"``{index_str.ljust(3)}`` \u200b \u200b\u200b \u200b\u200b \u200b \u200b \u200b \u200b \u200b\n"
    #    tag_string += "\u200b \n"

    # Signup dates
    signup_string = f"__{signup_start_date.strftime('%a')} {signup_start_date.strftime('%b')} {signup_start_date.day} {signup_start_date.year}__ to __{signup_end_date.strftime('%a')} {signup_end_date.strftime('%b')} {signup_end_date.day} {signup_end_date.year}__"

    # Create the embed
    embed = discord.Embed(title=f":trophy: {cup_name}", color=0xFFD700, description=f"Mandatory number of **active** players in roster: between ``{cup_info['mini_roster']}`` and ``{cup_info['maxi_roster']}``")
    embed.add_field(name="Team", value= team_string, inline=True)
    embed.add_field(name="Tag", value= tag_string, inline=True)
    embed.add_field(name="Total", value= f"``{len(team_ids)}`` Teams signed up", inline=False)
    embed.add_field(name="Signup dates", value= signup_string, inline=False)

    return embed

async def division(bot, cup_id, div_number):
    # Get cup info
    bot.cursor.execute("SELECT * FROM Cups WHERE id=%d", (cup_id,))

    # Fetch signed up teams
    bot.cursor.execute("SELECT team_id FROM Signups WHERE cup_id=%d AND div_number=%s", (cup_id, div_number))
    team_ids = bot.cursor.fetchall()

    tag_string = ""
    score_string = ""
    wdl_string = ""

    roster_channel = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_id)

    #Create embed field content
    if team_ids:
        for i, team_id in enumerate(team_ids):
            # Get team info
            bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (team_id['team_id'],))
            team_info = bot.cursor.fetchone()
            team_name = utils.prevent_discord_formating(team_info['name'])
            team_flag = flag.flagize(team_info['country'])
            team_tag_str = utils.prevent_discord_formating(team_info['tag'])
            index_str = str(i + 1) + "."

            # Get roster link
            roster_message = await roster_channel.fetch_message(team_info['roster_message_id'])
            roster_link = roster_message.jump_url

            tag_string += f"``{index_str.ljust(3)}`` {team_flag} {team_tag_str}\n" #[{team_tag_str}]({roster_link})\n"
            score_string += "``0``\n"
            wdl_string += "``8/5/2``\n"
        
    else:
        score_string = "\u200b"
        wdl_string = "\u200b"
        tag_string = "No team in div"


    # Create the embed
    embed = discord.Embed(title=f"Division {div_number}", color=0xFFD700)
    embed.add_field(name="Team", value= tag_string, inline=True)
    embed.add_field(name="W/D/L", value= wdl_string, inline=True)
    embed.add_field(name="Points", value= score_string, inline=True)

    return embed

async def map_list(bot, map_list, title, message):
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
        await map_list_message.add_reaction(bot.number_emojis[i])
        applied_reaction_emojis.append(bot.number_emojis[i].name)

    # TODO: drop list
     # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
    def check_reaction(reaction, user):
            return user.id != bot.user.id and reaction.message == map_list_message and reaction.emoji.name in applied_reaction_emojis
    reaction, _ = await bot.wait_for('reaction_add', check=check_reaction)

    # Get the choice
    map_choice = map_list[applied_reaction_emojis.index(reaction.emoji.name)]

    return map_choice


def fixture(bot, team1_id, team2_id, date, format):

    # Get teams info
    bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (team1_id,))
    team1 = bot.cursor.fetchone()
    bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (team2_id,))
    team2 = bot.cursor.fetchone()

    # Get date and time if set yet
    if date:
        fixture_date_elems = date.split(" ")
        fixture_date = fixture_date_elems[0]
        fixture_time = fixture_date_elems[1]
    else:
        fixture_date = "-"
        fixture_time = "-"

    embed = discord.Embed(color=0xFFD700, title=f"{flag.flagize(team1['country'])} {utils.prevent_discord_formating(team1['tag'])} :black_small_square: vs :black_small_square: {utils.prevent_discord_formating(team2['tag'])} {flag.flagize(team2['country'])}", description= format)
    embed.add_field(name=":pencil: Status", value= "-", inline=True)
    embed.add_field(name=":calendar_spiral: Date", value= fixture_date, inline=True)
    embed.add_field(name=":alarm_clock: Time (CET)", value= fixture_time, inline=True)
    embed.add_field(name=":map: Map TS", value= f"-", inline=True)
    embed.add_field(name=":map: Map CTF", value= f"-", inline=True)
    embed.add_field(name=":link: Demo and MOSS", value= f"https://dev.urt.li", inline=True)

    return embed

async def match_index(bot, cup_id, channel):
    # Get fixtures 
    bot.cursor.execute("SELECT * FROM Fixtures WHERE cup_id=%d", (cup_id,))
    fixtures = bot.cursor.fetchall()

    #Create embed field content
    fixture_string = "Matches not scheduled \n\n"
    if fixtures:
        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"``{index_str.ljust(3)}`` {fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)

        fixture_string = "~ \n\nMatches scheduled but not played \n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"``{index_str.ljust(3)}`` {fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)

        fixture_string = "~ \n\nMatches in progress \n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"``{index_str.ljust(3)}`` {fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)

        fixture_string = "~ \n\nMatches finished \n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"``{index_str.ljust(3)}`` {fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)

    '''   
    else:
        fixture_string = "\u200b"

    print(len(fixture_string))
    # Create the embed
    embed = discord.Embed(title=f":dividers: Match index", color=0xFFD700, description=f"Click on a game to jump to their channel")
    embed.add_field(name="Matches not scheduled", value= fixture_string, inline=False)
    embed.add_field(name="Matches scheduled but not played", value= fixture_string, inline=True)
    embed.add_field(name="Matches in progress", value= fixture_string, inline=False)
    embed.add_field(name="Matches finsihed", value= fixture_string, inline=False)

    return embed
    '''