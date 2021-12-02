import datetime
import os
from typing import Union

import mariadb
from ftwgl import FTWClient, UserTeamRole, MatchType
import asyncio

from cogs.common.utils import create_abbreviation

if __name__ == "__main__":
    conn = mariadb.connect(
        user="dev",
        password=os.getenv('DBPASSWORD'),
        host=os.getenv('DBIP'),
        port=3306,
        database=os.getenv('DBNAME')
    )
    cursor = conn.cursor(dictionary=True)

    ftw_client = FTWClient(
        ftw_host=os.getenv("FTW_HOST"),
        ftw_api_key=os.getenv("FTW_API_KEY")
    )

    def roster_accepted_to_user_team_role(accepted: int) -> Union[UserTeamRole, None]:
        if accepted == 0:
            return UserTeamRole.invited
        elif accepted == 1:
            return UserTeamRole.member
        elif accepted == 2:
            return UserTeamRole.leader
        elif accepted == 3:
            return UserTeamRole.inactive
        else:
            return None

    async def data_backfill():
        # Migrate users
        cursor.execute("SELECT * FROM Users")
        users = cursor.fetchall()
        for user in users:
           await ftw_client.user_create_or_update(
               discord_id=user['discord_id'],
               discord_username=user['ingame_name'],
               urt_auth=user['urt_auth']
           )

        # Migrate teams
        cursor.execute("""SELECT t.id as team_id, u.discord_id, t.name, t.tag
                            FROM Teams t
                            JOIN Users u ON (t.captain = u.id)
                            WHERE ftw_team_id IS NULL""")
        teams = cursor.fetchall()
        for team in teams:
            ftw_team_id = await ftw_client.team_create(
                creator_discord_id=team['discord_id'],
                team_name=team['name'],
                team_tag=team['tag']
            )
            if ftw_team_id is not None:
                cursor.execute("UPDATE Teams SET ftw_team_id = %s WHERE id = %s", (ftw_team_id, team['team_id'],))
                conn.commit()

        # Migrate roster
        cursor.execute("""
            SELECT r.accepted, u.discord_id, t.ftw_team_id
              FROM Roster r 
              JOIN Users u ON (r.player_id = u.id)
              JOIN Teams t ON (r.team_id = t.id)""")
        roster = cursor.fetchall()
        for team_user in roster:
            userTeamRole = roster_accepted_to_user_team_role(team_user['accepted'])
            if userTeamRole is not None:
                await ftw_client.team_add_user_or_update_role(
                    team_id=team_user['ftw_team_id'],
                    discord_id=team_user['discord_id'],
                    role=userTeamRole
                )

        # Migrate cups
        cursor.execute("SELECT * FROM Cups WHERE ftw_cup_id IS NULL")
        cups = cursor.fetchall()
        for cup in cups:
            signup_start_date = datetime.datetime.strptime(cup['signup_start_date'], '%Y-%m-%d %H:%M:%S')
            signup_end_date = datetime.datetime.strptime(cup['signup_end_date'], '%Y-%m-%d %H:%M:%S')
            ftw_cup_id = await ftw_client.cup_create(
                name=cup['name'],
                abbreviation=create_abbreviation(cup['name']),
                playoff_length=None,
                minimum_roster_size=cup['mini_roster'],
                start_date=signup_start_date,
                roster_lock_date=signup_end_date
            )
            if ftw_cup_id is not None:
                cursor.execute("UPDATE Cups SET ftw_cup_id = %s WHERE id = %s",
                               (ftw_cup_id, cup['id'],))
                conn.commit()

        # Migrate cup signups
        cursor.execute("""SELECT s.*, c.ftw_cup_id, t.ftw_team_id
                          FROM Signups s 
                          JOIN Cups c ON (s.cup_id = c.id)
                          JOIN Teams t ON (s.team_id = t.id)""")
        signups = cursor.fetchall()
        for signup in signups:
            await ftw_client.cup_add_team(
                team_id=signup['ftw_team_id'],
                cup_id=signup['ftw_cup_id']
            )
            await ftw_client.cup_set_team_division(
                team_id=signup['ftw_team_id'],
                cup_id=signup['ftw_cup_id'],
                division=signup['div_number']
            )


        # Migrate fixtures
        cursor.execute("""SELECT f.*, c.ftw_cup_id, t1.ftw_team_id as ftw_team1_id, t2.ftw_team_id as ftw_team2_id
                            FROM Fixtures f
                            JOIN Cups c ON (f.cup_id = c.id)
                            JOIN Teams t1 ON (f.team1 = t1.id)
                            JOIN Teams t2 ON (f.team2 = t2.id)
                            WHERE ftw_match_id IS NULL
                        """)
        fixtures = cursor.fetchall()
        for fixture in fixtures:
            match_date = None
            if fixture['date'] is not None:
                match_date = datetime.datetime.strptime(fixture['date'], '%Y-%m-%d %H:%M:%S')
            ftw_match_id = await ftw_client.match_create(
                cup_id=fixture['ftw_cup_id'],
                team_ids=[fixture['ftw_team1_id'], fixture['ftw_team2_id']],
                best_of=int(fixture['format'][2]),
                match_type=MatchType.group,
                match_date=match_date
            )
            if ftw_match_id is not None:
                cursor.execute("UPDATE Fixtures SET ftw_match_id = %s WHERE id = %s", (ftw_match_id, fixture['id'],))
                conn.commit()

    asyncio.run(data_backfill())
