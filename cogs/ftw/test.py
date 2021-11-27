from api import FTWClient
from datetime import datetime, timedelta
import asyncio
from models import UserTeamRoles, MatchType, GameTypes


async def test():
    ftw_client = FTWClient()

    cup_start = datetime.now()
    cup_id = await ftw_client.cup_create('Team Survivor', 'TS', 3, 5, cup_start, cup_start + timedelta(days=10))

    await ftw_client.user_create(12345, 'soli', 'soli')
    team1_id = await ftw_client.team_create(12345, 'x`  or', 'xor-')

    await ftw_client.user_create(54321, 'kenny', 'kenny')
    team2_id = await ftw_client.team_create(54321, 'Get Legit and Dip', 'GlaD*')

    await ftw_client.cup_add_team(team1_id, cup_id)
    await ftw_client.cup_add_team(team2_id, cup_id)

    await ftw_client.cup_set_team_division(cup_id, team1_id, 1)
    await ftw_client.cup_set_team_division(cup_id, team2_id, 2)

    await ftw_client.team_add_user(team1_id, 54321, UserTeamRoles.member)

    await ftw_client.team_add_user(team2_id, 12345, UserTeamRoles.member)
    await ftw_client.team_remove_user(team2_id, 12345)

    await ftw_client.team_add_user(team1_id, 54321, UserTeamRoles.captain)

    # cup_id = 3
    # team1_id = 1
    # team2_id = 2
    match_id = await ftw_client.match_create(cup_id, [team1_id, team2_id], 2, 1, MatchType.group, datetime.now())
    print(match_id)
    # servers = await ftw_client.server_locations()
    # print(servers)
    # server_id = await ftw_client.server_rent(match_id, 6, GameTypes.team_survivor, rcon="lol", password="lol", ttl_hours=1)
    # print(server_id)
    #
    # servers = await ftw_client.server_active()
    # print(servers)

asyncio.run(test())
