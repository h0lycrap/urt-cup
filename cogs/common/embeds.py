import discord
from discord_components import component
import flag
import re
import datetime
from cogs.common.enums import RosterStatus
import cogs.common.utils as utils
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component

def player(bot, auth):
    player = bot.db.get_player(urt_auth=auth)

    ds_player = discord.utils.get(bot.guilds[0].members, id=int(player['discord_id']))
    embed=discord.Embed(title=f"{flag.flagize(player['country'])} \u200b {player['ingame_name']}", color=0x9b2ab2)
    embed.add_field(name="Auth", value= player['urt_auth'], inline=False)
    embed.set_thumbnail(url=ds_player.avatar_url)

    # Get player's teams
    teams = bot.db.get_teams_player(player['id'])

    # If the player is in no team
    if not teams:
        teams_str="."

    else:
        teams_str=""
        for team in teams:
            # Get team country
            team_info = bot.db.get_clan(id=team['team_id'])

            # If he is a member of the team
            if int(team['accepted']) == 1:
                teams_str += f"{flag.flagize(team_info['country'])} \u200b {utils.prevent_discord_formating(team_info['tag'])}\n"

            # If he is the captain of the team
            elif int(team['accepted']) == 2:
                teams_str += f"{flag.flagize(team_info['country'])} \u200b {utils.prevent_discord_formating(team_info['tag'])} (Captain)\n"

            # If he is inactive
            elif int(team['accepted']) == 3:
                teams_str += f"{flag.flagize(team_info['country'])} \u200b {utils.prevent_discord_formating(team_info['tag'])} (Inactive)\n" 

        if teams_str == "":
            teams_str = "."

    embed.add_field(name="Clans", value= teams_str, inline=True)

    return embed

def team(bot, tag, show_invited=False): 
    mini_number_players = 1

    # Get the team info
    team = bot.db.get_clan(tag=tag)
    country = flag.flagize(team['country'])
    #captain = discord.utils.get(bot.guilds[0].members, id=int(team['captain']))
    name = team['name']
    discord_link = team['discord_link']

    # Get captain info
    captain = bot.db.get_player(id=team['captain'])

     # Get the players for each team
    players = bot.db.get_players_of_team(team['id'])

    # Filter out unaccepted invites and check if there are the minimum number of players to display in the roster
    accepted_players = list(filter(lambda x: x['accepted'] != RosterStatus.Invited.value, players))

    # Get the members 
    members = list(filter(lambda x: x['accepted'] == RosterStatus.Member.value or x['accepted'] == RosterStatus.Captain.value, accepted_players))

    # Get the inactives 
    inactives= list(filter(lambda x: x['accepted'] == RosterStatus.Inactive.value, accepted_players))

    # Get inactive name list
    if len(inactives) == 0:
        inactive_string = "None"
    else:
        inactive_string = ""
        for inactive in inactives[:-1]:

            # Get inactive info
            inactive_info = bot.db.get_player(id=inactive['player_id'])
            inactive_string += f"{flag.flagize(inactive_info['country'])} {inactive_info['ingame_name']}, "

        inactive_info = bot.db.get_player(id=inactives[-1]['player_id'])
        inactive_string += f"{flag.flagize(inactive_info['country'])} {utils.prevent_discord_formating(inactive_info['ingame_name'])}"


    # Get the list of invited players
    invited_players = list(filter(lambda x: x['accepted'] == 0, players))

    # Generate roster body
    roster_str1 = ""
    roster_str2 = "\u200b"
    roster_invited = ""
    for i, player in enumerate(members):

        # Get player country flag and urt auth
        player_info = bot.db.get_player(id=player['player_id'])
        if not player_info:
            player_auth_str = "urtauth"
            player_flag_str = ":FR:"
        else:
            player_auth_str = player_info['urt_auth']
            player_flag_str = player_info['country']

        player_string = f"{flag.flagize(player_flag_str)} {utils.prevent_discord_formating(player_info['ingame_name'])} ``[{player_auth_str}]``\n"
        # Check if we add in the first column or the second one
        if i % 2 == 0:
            roster_str1 += player_string
        else:
            roster_str2 += player_string

    # Invited players loop
    for i, player in enumerate(invited_players):
        # Get player country flag and urt auth
        player_info = bot.db.get_player(id=player['player_id'])
        if not player_info:
            player_auth_str = "urtauth"
            player_flag_str = ":FR:"
        else:
            player_auth_str = player_info['urt_auth']
            player_flag_str = player_info['country']

        roster_invited += f"{flag.flagize(player_flag_str)} {utils.prevent_discord_formating(player_info['ingame_name'])} ``[{player_auth_str}]``\n"

    # Create embed
    embed=discord.Embed(title=f"{utils.prevent_discord_formating(name)} {country}", color=13695009)
    embed.add_field(name=f"**Captain: **{utils.prevent_discord_formating(captain['ingame_name'])}     |     **Tag: **{utils.prevent_discord_formating(tag)}", value= "\u200b", inline=False)
    embed.add_field(name="Members [auth] ", value= roster_str1, inline=True)
    embed.add_field(name="\u200b", value=roster_str2, inline=True)
    if show_invited and roster_invited != "":
        embed.add_field(name="Invited", value=roster_invited, inline=False)
    embed.add_field(name="Inactives", value=inactive_string, inline=False)
    embed.add_field(name="Discord", value=discord_link, inline=True)
    embed.add_field(name="Awards", value="None", inline=True) # Hardcoded for now

    return embed, len(accepted_players) < mini_number_players


async def team_index(bot, admin_managed):

    # Fetch teams with a message id not null
    teams = bot.db.get_all_clans(admin_managed=admin_managed)

    # Sort the teams alphabetically on letters only
    sorted_teams = sorted(teams, key = lambda x: re.sub('[^A-Za-z]+', '', x['tag']).lower())

    modules = []
    index_str_left = ""
    index_str_right = ""

    # Build embed content
    roster_channel = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_id)
    if admin_managed == 1:
        roster_channel = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_national_teams_id)

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

        # Create a new module if the limit is reached
        if len(index_str_left) > 900 and len(index_str_right) > 900:
            modules.append([index_str_left, index_str_right])
            index_str_left = ""
            index_str_right = ""


    if len(index_str_right) == 0 and len(modules) == 0:
        index_str_right = "\u200b"
        
    if len(index_str_left) == 0 and len(modules) == 0:
        index_str_left = "\u200b"

    if len(index_str_left) > 0 and len(modules) > 0:
        modules.append([index_str_left, index_str_right])

    # Get total number of players in teams
    total_players = bot.db.get_total_player_teams(admin_managed)

    # Create the embed
    embed = discord.Embed(title=f":pencil: Clan index", color=0xFFD700, description="Click on a clan tag to jump to their roster")
    if len(modules) == 0:
        embed.add_field(name="Teams", value= index_str_left, inline=True)
        embed.add_field(name="\u200b", value= index_str_right, inline=True)
    else:
        for (i, module) in enumerate(modules):
            if i == 0:
                lefttitle = "Teams"
            else:
                lefttitle = "\u200b"

            if len(module[0]) == 0:
                module[0] = "\u200b"
            if len(module[1]) == 0:
                module[1] = "\u200b"

            embed.add_field(name=lefttitle, value= module[0], inline=True)
            embed.add_field(name="\u200b", value= module[1], inline=True)
            embed.add_field(name="\u200b", value= "\u200b", inline=True)

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
    cup_info = bot.db.get_cup(id=cup_id)
    cup_name = cup_info['name']
    signup_start_date = datetime.datetime.strptime(cup_info['signup_start_date'], '%Y-%m-%d %H:%M:%S')
    signup_end_date = datetime.datetime.strptime(cup_info['signup_end_date'], '%Y-%m-%d %H:%M:%S')

    # Fetch signed up teams
    team_ids = bot.db.get_cup_signups(cup_id)

    team_string = ""
    tag_string = ""

    roster_channel = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_id)
    roster_channel2 = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_national_teams_id)

    #Create embed field content
    if team_ids:
        for i, team_id in enumerate(team_ids):
            # Get team info
            team_info = bot.db.get_clan(id=team_id['team_id'])
            team_name = utils.prevent_discord_formating(team_info['name'])
            team_flag = flag.flagize(team_info['country'])
            team_tag_str = utils.prevent_discord_formating(team_info['tag'])

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
    # Fetch signed up teams
    team_signup_infos = bot.db.get_cup_signups(cup_id=cup_id, div_number=div_number)
    cup_info = bot.db.get_cup(id=cup_id)

    tag_string = ""
    score_string = ""
    wdl_string = ""

    #Create embed field content
    if team_signup_infos:
        # Sort by poitns
        for i, team_signup_info in enumerate(team_signup_infos):
            if not team_signup_info['points']:
                team_signup_infos[i]['points'] = 0
            if not team_signup_info['win']:
                team_signup_infos[i]['win'] = 0
            if not team_signup_info['draw']:
                team_signup_infos[i]['draw'] = 0
            if not team_signup_info['loss']:
                team_signup_infos[i]['loss'] = 0
        
        team_signup_infos = sorted(team_signup_infos, key=lambda k: k['points'], reverse=True)

        for i, team_signup_info in enumerate(team_signup_infos):
            # Get team info
            team_info = bot.db.get_clan(id=team_signup_info['team_id'])
            team_name = utils.prevent_discord_formating(team_info['name'])
            team_flag = flag.flagize(team_info['country'])
            team_tag_str = utils.prevent_discord_formating(team_info['tag'])
            index_str = str(i + 1) + "."

            tag_string += f"``{index_str.ljust(3)}`` {team_flag} {team_tag_str}\n" #[{team_tag_str}]({roster_link})\n"

            score_string += f"\u200b \u200b \u200b \u200b \u200b ``{team_signup_info['points']}``\n"
            wdl_string += f"``{team_signup_info['win']}``/``{team_signup_info['draw']}``/``{team_signup_info['loss']}``\n"
        
    else:
        score_string = "\u200b"
        wdl_string = "\u200b"
        tag_string = "No team in div"


    # Create the embed
    embed = discord.Embed(title=f"Division {div_number}", color=0xFFD700)
    # TEMPORARY JUST FOR QUALIFIERS TODO 
    #embed = discord.Embed(title=f"Qualifiers", color=0xFFD700)
    embed.add_field(name="Team", value= tag_string, inline=True)
    embed.add_field(name="W/D/L", value= wdl_string, inline=True)
    embed.add_field(name="Points", value= score_string, inline=True)
    embed.description = "Detailed ranking: [Click here](https://ggle.io/5Vou)"
    if "CTF" in cup_info['name']:
        embed.description = "Detailed ranking: [Click here](https://ggle.io/5Vp8)"

    return embed

def map_list(map_list, title):
    maps_string = ""
    for (i, map_info) in enumerate(map_list):
        index_str = (str(i + 1) + ".").ljust(2)
        maps_string += f"``{index_str}`` {map_info['name']}\n"

    # Create clan list embed
    embed = discord.Embed(title=title, color=0xFFD700)
    embed.add_field(name="Map", value= maps_string, inline=True)

    return embed


async def fixture(bot, fixture_id=None, team1_id=None, team2_id=None, date=None, format=None, status=None):
    # Get fixture info
    fixture_info = bot.db.get_fixture(id=fixture_id)
    if fixture_info:
        team1_id = fixture_info['team1']
        team2_id = fixture_info['team2']
        date = fixture_info['date']
        status = fixture_info['status']
        format = fixture_info['format']
        fixture_id = fixture_info['id']


    # Get teams info
    team1 = bot.db.get_clan(id=team1_id)
    team2 = bot.db.get_clan(id=team2_id)

    # Get maps info
    maps = bot.db.get_fixture_maps(fixture_id)

    map_string = ""
    if maps:
        for map in maps:
            map_info = bot.db.get_map(map['map_id'])
            map_string += f"{map_info['name']}\n"
    
    if len(map_string) == 0:
        map_string = "-"

    # Get date and time if set yet
    if date:
        timestamp = utils.get_timestamp(date)
        fixture_date = f"<t:{timestamp}:d>"
        fixture_time = f"<t:{timestamp}:t>"
    else:
        fixture_date = "-"
        fixture_time = "-"

    # Get status
    if status and int(status) == 1:
        status_str = "Scheduled"
    elif status and int(status) == 2:
        status_str = "In progress"
    elif status and int(status) >= 3:
        status_str = "Finished"
    else:
        status_str = "Not scheduled"

    roster_channel = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_id)
    roster_channel2 = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_national_teams_id)

    try:
        roster_message1 = await roster_channel.fetch_message(team1['roster_message_id'])
        roster_message1 = roster_message1.jump_url
    except:
        try:
            roster_message1 = await roster_channel2.fetch_message(team1['roster_message_id'])
            roster_message1 = roster_message1.jump_url
        except:
            roster_message1 = ""

    try:
        roster_message2 = await roster_channel.fetch_message(team2['roster_message_id'])
        roster_message2 = roster_message2.jump_url
    except:
        try:
            roster_message2 = await roster_channel2.fetch_message(team2['roster_message_id'])
            roster_message2 = roster_message2.jump_url
        except:
            roster_message2 = ""
            


    #team_string = f"{team_flag} [{utils.prevent_discord_formating(team_tag)}]({roster_message.jump_url})\n"

    embed = discord.Embed(color=0xFFD700, title=f"{flag.flagize(team1['country'])} {utils.prevent_discord_formating(team1['tag'])} :black_small_square: vs :black_small_square: {utils.prevent_discord_formating(team2['tag'])} {flag.flagize(team2['country'])}", description= f"**Format: **{format} \u200b \u200b **|** \u200b \u200b **Rosters**: [{utils.prevent_discord_formating(team1['tag'])}]({roster_message1}) \u200b \u200b [{utils.prevent_discord_formating(team2['tag'])}]({roster_message2})")
    embed.add_field(name=":pencil: Status", value= status_str, inline=True)
    embed.add_field(name=":calendar_spiral: Date (D/M/Y)", value= fixture_date, inline=True)
    embed.add_field(name=":alarm_clock: Time", value= fixture_time, inline=True)
    embed.add_field(name=":map: Maps", value= map_string, inline=True)
    embed.add_field(name=":link: MOSS", value= f"DM Holycrap", inline=True)

    components = [[
            Button(style=ButtonStyle.blue, label="Schedule", custom_id=f"button_fixture_schedule", emoji="\U0001F4C5"),
            Button(style=ButtonStyle.blue, label="Pick & ban", custom_id=f"button_fixture_startpickban", emoji="\U0001F5FA"),
            Button(style=ButtonStyle.blue, label="Request a server", custom_id=f"button_fixture_requestserver", emoji="\U0001F5A5"),
            Button(style=ButtonStyle.grey, label="Admin Panel", custom_id=f"button_edit_fixture")
            ],
            [
            Button(style=ButtonStyle.green, label="Launch AC", custom_id=f"button_launch_ac", emoji="\U0001F3AE") 
            ]]

    return embed, components

async def match_index(bot, cup_id, channel):
    # Get fixtures 
    fixtures = bot.db.get_cup_fixtures(cup_id)

    #Create embed field content
    fixture_string = "Matches not scheduled \n\n"
    if fixtures:
        '''
        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."
            
            # Get status
            if fixture_info['status'] != None:
                continue

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"{fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)
        '''
    
        

        fixture_string = "**Scores need to be entered**\n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get status
            if fixture_info['status'] != 2:
                continue

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"{fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)

        fixture_string = "~ \n\n**Schedule needs to be forced**\n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get status
            if fixture_info['status'] != None or not fixture_info['date_last_proposal']:
                continue

            # Get the number of hours since the last proposal was sent 
            gamedate = datetime.date.fromisoformat(fixture_info['date_last_proposal'].split()[0])
            gametime = datetime.time.fromisoformat(fixture_info['date_last_proposal'].split()[1])
            gameschedule = datetime.datetime.combine(gamedate, gametime)

            deltatime = datetime.datetime.now() - gameschedule

            if not deltatime.days >= 5:
                continue

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"{fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)

        fixture_string = "~ \n\n**Scheduled but not played** (might need a Streamer)\n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get status
            if fixture_info['status'] != 1:
                continue

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"{fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)
        '''

        fixture_string = "~ \n\nMatches finished \n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get status
            if fixture_info['status'] != 3:
                continue

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"{fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)

        
        fixture_string = "~ \n\nMatches finished with missing Moss or demo Files from more than 50h \n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get status
            if fixture_info['status'] != 4:
                continue

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"{fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)

        fixture_string = "~ \n\nMatches archived \n\n"

        for i, fixture_info in enumerate(fixtures):
            index_str = str(i + 1) + "."

            # Get status
            if fixture_info['status'] != 5:
                continue

            # Get fixture link
            fixture_channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))

            fixture_string += f"{fixture_channel.mention}\n"

            if len(fixture_string) > 1900:
                await channel.send(fixture_string)
                fixture_string = ""

        await channel.send(fixture_string)
        '''


def calendar(bot, cup_info):
    # Get fixtures 
    fixtures = bot.db.get_cup_fixtures(cup_info['id'])

    fixture_list = []
    date_list = []
    TBD_date = 9999999999
    for fixture in fixtures:
        if fixture['status'] and int(fixture['status']) >= 3:
            continue

        team1 = bot.db.get_clan(id=fixture['team1'])
        team2 = bot.db.get_clan(id=fixture['team2'])

        fixture_list.append([flag.flagize(team1['country']), utils.prevent_discord_formating(team1['tag']), flag.flagize(team2['country']), utils.prevent_discord_formating(team2['tag'])])

        

        # Filter unscheduled and finished matches
        if not fixture['status']:
            date_list.append(TBD_date)
        else:
            date_list.append(utils.get_timestamp(fixture['date']))
    
    sorted_index = sorted(range(len(date_list)), key=lambda k: date_list[k])

    fixture_str1 = ""
    fixture_str2 = ""
    date_str = ""
    modules = []
    for i in sorted_index:
        fixture_str1 += f"{fixture_list[i][0]}  {fixture_list[i][1]}\n \n" 
        fixture_str2 += f"{fixture_list[i][2]}  {fixture_list[i][3]}\n \n" 

        if date_list[i] != TBD_date:
            date_str += f"<t:{date_list[i]}:d>  -  <t:{date_list[i]}:t> \n \n"
        else:
            date_str += "--/--  -  --:-- \n \n"
            

        # Create a new module if the limit is reached
        if len(fixture_str1) > 900 or len(fixture_str2) > 900 or len(date_str) > 900:
            modules.append([date_str, fixture_str1, fixture_str2])
            fixture_str1 = ""
            fixture_str2 = ""
            date_str = ""


    if len(date_str) == 0 and len(modules) == 0:
        date_str = "\u200b"
        
    if len(fixture_str1) == 0 and len(modules) == 0:
        fixture_str1 = "\u200b"
        fixture_str2 = "\u200b"

    if len(fixture_str1) > 0 and len(modules) > 0:
        modules.append([date_str, fixture_str1, fixture_str2])

    # Create the embed
    embed = discord.Embed(title=f":calendar_spiral: Calendar", color=13568619)
    title1 = "\u200b \u200b Date \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b\n \u200b"
    title2 = "\u200b \u200b \u200bTeam 1\u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b   VS  \u200b \u200b \u200b \n \u200b"
    title3 = "\u200b \u200b \u200bTeam 2 \n \u200b"
    if len(modules) == 0:
        embed.add_field(name=title1, value= date_str, inline=True)
        embed.add_field(name=title2, value= fixture_str1, inline=True)
        embed.add_field(name=title3, value= fixture_str2, inline=True)

    else:
        for (i, module) in enumerate(modules):
            if i != 0:
                title1 = "\u200b"
                title2 = "\u200b"
                title3 = "\u200b"

            if len(module[0]) == 0:
                module[0] = "\u200b"
            if len(module[1]) == 0:
                module[1] = "\u200b"

            embed.add_field(name=title1, value= module[0], inline=True)
            embed.add_field(name=title2, value= module[1], inline=True)
            embed.add_field(name=title3, value= module[2], inline=True)

    #embed.set_footer(text=f"Total: {len(sorted_teams)} Teams, {len(total_players)} Players")

    return embed

def results(bot, fixture_info, match_type):

    # Format date
    fixture_schedule_elems = str(fixture_info['date']).split(" ")
    fixture_date_elems = fixture_schedule_elems[0].split('-')
    fixture_date = f"{fixture_date_elems[2]}/{fixture_date_elems[1]}"#/{fixture_date_elems[0]}"
    fixture_time_elems = fixture_schedule_elems[1].split(':')
    fixture_time = f"{fixture_time_elems[0]}:{fixture_time_elems[1]}"
    date_str = f"{fixture_date} - {fixture_time}"

    # Get teams info
    team1 = bot.db.get_clan(id=fixture_info['team1'])
    team2 = bot.db.get_clan(id=fixture_info['team2'])

    # Get maps info
    maps = bot.db.get_fixture_maps(fixture_info['id'])

    map_str = ""
    score_str = ""
    for i in range(len(maps)):
        map_info = bot.db.get_map(maps[i]['map_id'])
        map_str += f"**{map_info['name']}** *({map_info['gamemode']})*"
        score_str += f"**{maps[i]['team1_score']}-{maps[i]['team2_score']}**"
        if i < len(maps) - 1:
            map_str += "  /  "
            score_str += "  /  "

    result_str = f"**[{match_type.capitalize()}]**    **|**    :calendar_spiral: {date_str}    **|**    {flag.flagize(team1['country'])} **{utils.prevent_discord_formating(team1['tag'])}**  vs  {flag.flagize(team2['country'])} **{utils.prevent_discord_formating(team2['tag'])}**    **|**    :map: : {map_str}    **|**    :dart: : {score_str}"
    return result_str


def streamer_avi(team1, team2, date, strmavi_list=[], shtavi_list=[]):

    timestamp = utils.get_timestamp(date)
    date_str = f"<t:{timestamp}:d>  -  <t:{timestamp}:t>"

    strmavi=""
    for streamerid in strmavi_list:
        strmavi+= f"<@{streamerid}>\n"
    if strmavi == "":
        strmavi="None"

    shtavi=""
    for streamerid in shtavi_list:
        shtavi+= f"<@{streamerid}>\n"
    if shtavi == "":
        shtavi="None"
    
    e = discord.Embed(color=0xFFD700, title=f"{flag.flagize(team1['country'])} {team1['tag']} :black_small_square: vs :black_small_square: {team2['tag']} {flag.flagize(team2['country'])}", description=f":calendar_spiral: {date_str}")
    e.add_field(name="Streamer :eyes: : :black_small_square: ", value=strmavi, inline = True)
    e.add_field(name="Shoutcaster :microphone2: :", value=shtavi, inline = True)

    return e
