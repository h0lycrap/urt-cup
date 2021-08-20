from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption
import flag

def teams(clan_info_list, title, id): 
    select_options = []
    for (i, clan_info) in enumerate(clan_info_list):
        clan_flag = flag.flagize(clan_info['country'])
        select_options.append(SelectOption(label = clan_info['name'], emoji = clan_flag, value = i))

    return [Select( placeholder = title, options = select_options, custom_id=id)]

def players_of_team(bot, team_id, id, include_captain=False, include_invited=False): 
    # Get the players for each team
    bot.cursor.execute("SELECT * FROM Roster WHERE team_id = %s;", (team_id,))
    players = bot.cursor.fetchall()
    player_info_list = []
    for i, player in enumerate(players):
        # Exclude captain 
        if (not include_captain and player['accepted'] == 2) or (not include_invited and player['accepted'] == 0):
            continue
        bot.cursor.execute("SELECT* FROM Users WHERE id = %s;", (player['player_id'],))
        player_info_list.append(bot.cursor.fetchone())

    select_options = []
    for (i, player_info) in enumerate(player_info_list):
        player_flag = flag.flagize(player_info['country'])
        select_options.append(SelectOption(label = f"{player_info['ingame_name']} ({player_info['urt_auth']}) ", emoji = player_flag, value = i))

    return player_info_list, [Select(options = select_options, custom_id=id)]