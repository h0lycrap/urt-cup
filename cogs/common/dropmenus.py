from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption
import flag

def teams(clan_info_list, title, id): 
    select_options = []
    for (i, clan_info) in enumerate(clan_info_list):
        clan_flag = flag.flagize(clan_info['country'])
        select_options.append(SelectOption(label = clan_info['name'], emoji = clan_flag, value = i))

    return [Select( placeholder = title, options = select_options, custom_id=id)]

def formats(formats, title, id): 
    select_options = []
    for (i, format) in enumerate(formats):
        select_options.append(SelectOption(label = format, value = i))

    return [Select( placeholder = title, options = select_options, custom_id=id)]

def players_of_team(bot, team_id, id, include_captain=False, include_invited=False, include_members=True, include_inactive=False): 
    # Get the players for each team
    bot.cursor.execute("SELECT * FROM Roster WHERE team_id = %s;", (team_id,))
    players = bot.cursor.fetchall()
    player_info_list = []
    for i, player in enumerate(players):
        # Exclude captain and others
        if (not include_captain and player['accepted'] == 2) or (not include_invited and player['accepted'] == 0) or (not include_inactive and player['accepted'] == 3) or (not include_members and player['accepted'] == 1):
            continue
        bot.cursor.execute("SELECT* FROM Users WHERE id = %s;", (player['player_id'],))
        player_info_list.append(bot.cursor.fetchone())

    if len(player_info_list) == 0:
        return player_info_list, None

    select_options = []
    for (i, player_info) in enumerate(player_info_list):
        player_flag = flag.flagize(player_info['country'])
        select_options.append(SelectOption(label = f"{player_info['ingame_name']} ({player_info['urt_auth']}) ", emoji = player_flag, value = i))

    return player_info_list, [Select(options = select_options, custom_id=id)]

def maps(map_info_list, id): 
    select_options = []
    for (i, map_info) in enumerate(map_info_list):
        select_options.append(SelectOption(label = map_info['name'], value = i))

    return [Select( placeholder = "Pick a map", options = select_options, custom_id=id)]

def player_played(players_team, players_played = None):
    players_buttons_team = []
    players_buttons_team_sublist = []
    for player_team in players_team:
        if players_played and player_team['id'] in players_played:
            button_style = ButtonStyle.blue
        else:
            button_style = ButtonStyle.grey

        if len(players_buttons_team_sublist) < 5:
            players_buttons_team_sublist.append(Button(style=button_style, label=player_team['urt_auth'], custom_id=f"button_player_played_{player_team['player_id']}"))
        else:
            players_buttons_team.append(players_buttons_team_sublist)
            players_buttons_team_sublist = [Button(style=button_style, label=player_team['urt_auth'], custom_id=f"button_player_played_{player_team['player_id']}")]
    if len(players_buttons_team_sublist) != 0:
        players_buttons_team.append(players_buttons_team_sublist)
    players_buttons_team.append([
        Button(style=ButtonStyle.green, label="Validate", custom_id=f"button_player_played_validate")
    ])

    return players_buttons_team

def problems(problem_list, id): 
    select_options = []
    for (i, problem) in enumerate(problem_list):
        select_options.append(SelectOption(label = f"{problem[0]} {problem[1]}", value = i))

    return [Select( placeholder = "Select a problem to fix", options = select_options, custom_id=id)]