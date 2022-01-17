from discord import channel
import mariadb

from cogs.common.enums import RosterStatus

class Database():

    def __init__(self, user, ip, password, dbname):
        self.conn = mariadb.connect(
                user=user,
                password=password,
                host=ip,
                port=3306,
                database=dbname
            )
        self.cursor = self.conn.cursor(dictionary=True)

#----Players--------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def create_player(self, discord_id, urt_auth, ingame_name, country):
        self.cursor.execute("INSERT INTO Users(discord_id, urt_auth, ingame_name, country) VALUES (%s, %s, %s, %s) ;", (discord_id, urt_auth, ingame_name, country))
        self.conn.commit()
        

    def get_player(self, id=None, discord_id=None, urt_auth=None, ingame_name=None):
        sql = "SELECT * FROM Users WHERE "
        params = ()

        if id != None:
            sql += "id = %s "
            params += (id,)
        if discord_id != None:
            if len(params) > 0:
                sql += "AND "
            sql += "discord_id = %s "
            params += (discord_id,)
        if urt_auth != None:
            if len(params) > 0:
                sql += "AND "
            sql += "urt_auth = %s "
            params += (urt_auth,)
        if ingame_name != None:
            if len(params) > 0:
                sql += "AND "
            sql += "ingame_name = %s "
            params += (ingame_name,)
        if len(params) == 0:
            return None

        self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def edit_player(self, id, urt_auth=None, ingame_name=None, country=None, country_verified=None):
        sql = "UPDATE Users SET "
        params = ()

        if urt_auth != None:
            sql += "urt_auth = %s "
            params += (urt_auth,)
        if ingame_name != None:
            if len(params) > 0:
                sql += ", "
            sql += "ingame_name = %s "
            params += (ingame_name,)
        if country != None:
            if len(params) > 0:
                sql += ", "
            sql += "country = %s "
            params += (country,)
        if country_verified != None:
            if len(params) > 0:
                sql += ", "
            sql += "country_verified = %s "
            params += (country_verified,)
        if len(params) == 0:
            return
        sql += " WHERE id = %s"
        params += (id,)

        self.cursor.execute(sql, params)
        self.conn.commit()

    def delete_player(self, id):
        self.cursor.execute("DELETE FROM Users WHERE id = %s;", (id,))
        self.conn.commit()


#----Countries--------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def get_country(self, id=None):
        sql = "SELECT * FROM Countries WHERE "
        params = ()

        if id != None:
            sql += "id = %s "
            params += (id,)

        if len(params) == 0:
            return None

        self.cursor.execute(sql, params)
        return self.cursor.fetchone()


#----Clans--------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def create_clan(self, teamname, tag, country, captain, role_id, ftw_team_id, admin_managed):
        self.cursor.execute(
            "INSERT INTO Teams (name, tag, country, captain, role_id, ftw_team_id, admin_managed) VALUES (%s, %s, %s, %s, %s, %s, %s) ;",
            (teamname, tag, country, captain, role_id, ftw_team_id, admin_managed)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_clan(self, id=None, tag=None, name=None):
        sql = "SELECT * FROM Teams WHERE "
        params = ()

        if id != None:
            sql += "id = %s "
            params += (id,)
        if tag != None:
            if len(params) > 0:
                sql += "AND "
            sql += "tag = %s "
            params += (tag,)
        if name != None:
            if len(params) > 0:
                sql += "AND "
            sql += "name = %s "
            params += (name,)
        
        if len(params) == 0:
            return None

        self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def get_all_clans(self, admin_managed):
        self.cursor.execute("SELECT * FROM Teams WHERE admin_managed = %s;", (admin_managed,))
        return self.cursor.fetchall()

    def get_total_player_teams(self, admin_managed):
        self.cursor.execute("SELECT * FROM Roster INNER JOIN Teams ON Roster.team_id = Teams.id WHERE Teams.admin_managed = ?", (admin_managed,))
        return self.cursor.fetchall()


    def edit_clan(self, tag, newtag=None, name=None, captain=None, country=None, discord_link=None, roster_message_id=None):
        sql = "UPDATE Teams SET "
        params = ()

        if name != None:
            sql += "name = %s "
            params += (name,)
        if newtag != None:
            if len(params) > 0:
                sql += ", "
            sql += "tag = %s "
            params += (newtag,)
        if country != None:
            if len(params) > 0:
                sql += ", "
            sql += "country = %s "
            params += (country,)
        if captain != None:
            if len(params) > 0:
                sql += ", "
            sql += "captain = %s "
            params += (captain,)
        if discord_link != None:
            if len(params) > 0:
                sql += ", "
            sql += "discord_link = %s "
            params += (discord_link,)
        if roster_message_id != None:
            if len(params) > 0:
                sql += ", "
            sql += "roster_message_id = %s "
            params += (roster_message_id,)
        if len(params) == 0:
            return
        sql += " WHERE tag = %s"
        params += (tag,)

        self.cursor.execute(sql, params)
        self.conn.commit()

    def delete_clan(self, tag):
        self.cursor.execute("DELETE FROM Teams WHERE tag = %s;", (tag,))
        self.conn.commit()

    def get_teams_of_player(self, player_id, admin_managed=None):
        sql = "SELECT * FROM Teams WHERE captain = %s "
        params = (player_id,)

        if admin_managed != None:
            sql += "AND admin_managed = %s"
            params += (admin_managed,
            )
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def delete_team(self, team_id):
        self.cursor.execute("DELETE FROM Teams WHERE id = %s;", (team_id,))
        self.conn.commit()

        # Delete from roster
        self.cursor.execute("DELETE FROM Roster WHERE team_id = %s;", (team_id,))
        self.conn.commit()

        # Delete from signups
        self.cursor.execute("DELETE FROM Signups WHERE team_id = %s;", (team_id,))
        self.conn.commit()

    def get_clan_player_from_fixture(self, player_id, team1_id, team2_id):
        self.cursor.execute("SELECT * FROM Users AS u INNER JOIN Roster AS r ON u.id = r.player_id INNER JOIN Teams AS t ON r.team_id = t.id WHERE u.id = %s AND (t.id = %s OR t.id = %s)", (player_id, team1_id, team2_id))
        return self.cursor.fetchone()


#----Rosters--------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def create_roster_member(self, team_id, player_id, accepted):
        self.cursor.execute("INSERT INTO Roster(team_id, player_id, accepted) VALUES (%s, %s, %d) ;", (team_id, player_id, accepted.value))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_roster_member(self, player_id, team_id, accepted=None):
        sql = "SELECT * FROM Roster WHERE player_id = %s AND team_id = %s "
        params = (player_id, team_id)

        if accepted != None:
            sql += "AND accepted = %s "
            params += (accepted.value,)

        self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def get_players_of_team(self, team_id):
        self.cursor.execute("SELECT * FROM Roster WHERE team_id = %s;", (team_id,))
        return self.cursor.fetchall()

    def get_teams_player(self, player_id):
        self.cursor.execute("SELECT * FROM Roster WHERE player_id = %s;", (player_id,))
        return self.cursor.fetchall()

    def get_teams_player_member_inactive(self, player_id):
        self.cursor.execute("SELECT * FROM Roster WHERE player_id = %s AND (accepted=1 OR accepted=3);", (player_id,))
        return self.cursor.fetchall()

    def get_active_team_players(self, team_id):
        self.cursor.execute("SELECT * FROM Roster s INNER JOIN Users u ON s.player_id = u.id WHERE (s.accepted = 1 or s.accepted = 2) and s.team_id=%s;", (team_id,))
        return self.cursor.fetchall()

    def update_roster_status(self, status, player_id, team_id):
        self.cursor.execute("UPDATE Roster SET accepted=%s WHERE team_id = %s AND player_id=%s;", (status.value, team_id, player_id))
        self.conn.commit()

    def delete_player_from_roster(self, player_id, team_id=None):
        sql = "DELETE FROM Roster WHERE player_id = %s "
        params = (player_id,)

        if team_id != None:
            sql += "AND team_id=%s"
            params += (team_id,)
        self.cursor.execute(sql, params)
        self.conn.commit()


#----Signups--------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def clan_in_active_cup(self, team_id):
        self.cursor.execute("SELECT * FROM Signups INNER JOIN Cups ON Signups.cup_id = Cups.id WHERE Signups.team_id = %s AND Cups.status=1;", (team_id,))
        return self.cursor.fetchone()

    def get_teams_in_div(self, cup_id, div_number):
        self.cursor.execute("SELECT * FROM Signups s INNER JOIN Teams t ON s.team_id = t.id WHERE s.cup_id = %s and div_number=%s", (cup_id, div_number))
        return self.cursor.fetchall()

    def get_clan_signup(self, team_id, cup_id):
        self.cursor.execute("SELECT * FROM Signups WHERE team_id=%s and cup_id=%s", (team_id, cup_id))
        return self.cursor.fetchone()

    def signup_clan(self, team_id, cup_id):
        self.cursor.execute("INSERT INTO Signups (cup_id, team_id) VALUES (%d, %s);", (cup_id, team_id))
        self.conn.commit()

    def remove_signup_clan(self, team_id, cup_id):
        self.cursor.execute("DELETE FROM Signups WHERE team_id=%s and cup_id=%s", (team_id, cup_id))
        self.conn.commit()

    def get_cup_signups(self, cup_id, div_number=None, team_id=None):
        sql = "SELECT * FROM Signups WHERE cup_id=%s "
        params = (cup_id,)
        
        if div_number != None:
            sql += "AND div_number = %s "
            params += (div_number,)
        if team_id != None:
            sql += "AND team_id = %s"
            params += (team_id,)

        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def get_teams_nodiv_from_cup(self, cup_id):
        self.cursor.execute("SELECT * FROM Signups s INNER JOIN Teams t ON s.team_id = t.id WHERE s.cup_id = %s and div_number IS NULL", (cup_id,))
        return self.cursor.fetchall()

    def get_teams_div_from_cup(self, cup_id, div_number):
        self.cursor.execute("SELECT * FROM Signups s INNER JOIN Teams t ON s.team_id = t.id WHERE s.cup_id = %s and div_number = %s", (cup_id, div_number))
        return self.cursor.fetchall()

    def edit_signups(self, cup_id, team_id, div_number=None, points=None, win=None, draw=None ,loss=None):
        sql = "UPDATE Signups SET "
        params = ()

        if div_number != None:
            if div_number == 0:
                div_number = None
            sql += "div_number = %s "
            params += (div_number,)
        if points != None:
            if len(params) > 0:
                sql += ", "
            sql += "points = %s "
            params += (points,)
        if win != None:
            if len(params) > 0:
                sql += ", "
            sql += "win = %s "
            params += (win,)
        if draw != None:
            if len(params) > 0:
                sql += ", "
            sql += "draw = %s "
            params += (draw,)
        if loss != None:
            if len(params) > 0:
                sql += ", "
            sql += "loss = %s "
            params += (loss,)
        if len(params) == 0:
            return
        sql += " WHERE cup_id = %s AND team_id= %s"
        params += (cup_id, team_id)

        self.cursor.execute(sql, params)
        self.conn.commit()



#----Fixtures--------------------------------------------------------------------------------------------------------------------------------------------------------------------#
    def create_fixture(self, cup_id, team1, team2, format, channel_id, ftw_match_id):
        self.cursor.execute("INSERT INTO Fixtures (cup_id, team1, team2, format, channel_id, ftw_match_id) VALUES (%d, %s, %s, %s, %s, %s)", (cup_id, team1, team2, format, channel_id, ftw_match_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_fixture(self, id=None, team1=None, team2=None, channel_id=None):
        sql = "SELECT * FROM Fixtures WHERE "
        params = ()

        if id != None:
            sql += "id = %s "
            params += (id,)
        if team1 != None:
            if len(params) > 0:
                sql += "AND "
            sql += "team1 = %s "
            params += (team1,)
        if team2 != None:
            if len(params) > 0:
                sql += "AND "
            sql += "team2 = %s "
            params += (team2,)
        if channel_id != None:
            if len(params) > 0:
                sql += "AND "
            sql += "channel_id = %s "
            params += (channel_id,)
        
        if len(params) == 0:
            return None

        self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def edit_fixture(self, id, format=None, date=None, status=None, date_last_proposal=None, embed_id=None):
        sql = "UPDATE Fixtures SET "
        params = ()

        if format != None:
            sql += "format = %s "
            params += (format,)
        if date != None:
            if len(params) > 0:
                sql += ", "
            sql += "date = %s "
            params += (date,)
        if status != None:
            if len(params) > 0:
                sql += ", "
            sql += "status = %s "
            params += (status.value,)
        if date_last_proposal != None:
            if len(params) > 0:
                sql += ", "
            sql += "date_last_proposal = %s "
            params += (date_last_proposal,)
        if embed_id != None:
            if len(params) > 0:
                sql += ", "
            sql += "embed_id = %s "
            params += (embed_id,)
        if len(params) == 0:
            return
        sql += " WHERE id = %s"
        params += (id,)

        self.cursor.execute(sql, params)
        self.conn.commit()

    def delete_fixture(self, id):
        self.cursor.execute("DELETE FROM Fixtures WHERE id=%s", (id,))
        self.conn.commit()

    def get_fixtures_of_status(self, status):
        self.cursor.execute("SELECT * FROM Fixtures WHERE status=%s", (status.value,))
        return self.cursor.fetchall()

    def get_all_fixtures(self):
        self.cursor.execute("SELECT * FROM Fixtures WHERE status < 4;")
        return self.cursor.fetchall()

    def get_cup_fixtures(self, cup_id):
        self.cursor.execute("SELECT * FROM Fixtures WHERE cup_id = %s;", (cup_id,))
        return self.cursor.fetchall()

#----FixturePlayers--------------------------------------------------------------------------------------------------------------------------------------------------------------------#
    def create_fixture_player(self, fixture_id, player_id):
        self.cursor.execute("INSERT INTO FixturePlayer (fixture_id, player_id) VALUES (%s, %s)", (fixture_id, player_id))
        self.conn.commit()

    def delete_fixture_players(self, fixture_id):
        self.cursor.execute("DELETE FROM FixturePlayer WHERE fixture_id = %s", (fixture_id,))
        self.conn.commit()

    def get_fixture_players(self, fixture_id):
        self.cursor.execute("SELECT * FROM FixturePlayer WHERE fixture_id=%s", (fixture_id,))
        return self.cursor.fetchall()

    def edit_fixture_player(self, player_id, fixture_id, uploaded_moss=None, uploaded_demo=None):
        sql = "UPDATE FixturePlayer SET "
        params = ()

        if uploaded_moss != None:
            if len(params) > 0:
                sql += ", "
            sql += "uploaded_moss = %s "
            params += (uploaded_moss,)
        if uploaded_demo != None:
            if len(params) > 0:
                sql += ", "
            sql += "uploaded_demo = %s "
            params += (uploaded_demo,)
        if len(params) == 0:
            return
        sql += " WHERE player_id = %s AND fixture_id = %s"
        params += (player_id, fixture_id)

        self.cursor.execute(sql, params)
        self.conn.commit()

#----FixtureMaps--------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def get_fixture_maps(self, fixture_id):
        self.cursor.execute("SELECT * FROM FixtureMap WHERE fixture_id=%s", (fixture_id,))
        return self.cursor.fetchall()

    def create_fixture_map(self, fixture_id, map_id):
        self.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_id, map_id))
        self.conn.commit()

    def edit_fixture_map(self, id, team1_score, team2_score):
        self.cursor.execute("UPDATE FixtureMap set team1_score = %s, team2_score = %s WHERE id=%s", (team1_score, team2_score, id))
        self.conn.commit()

    def delete_fixture_maps(self, fixture_id):
        self.cursor.execute("DELETE FROM FixtureMap  WHERE fixture_id = %s", (fixture_id,))
        self.conn.commit()


#----Cups--------------------------------------------------------------------------------------------------------------------------------------------------------------------#
    def create_cup(self, name, mini_roster, signup_start_date, signup_end_date, category_id, chan_admin_id, chan_signups_id, chan_calendar_id, chan_stage_id, category_match_schedule_id, chan_match_index_id, maxi_roster, chan_results_id, ftw_cup_id):
        self.cursor.execute(
            "INSERT INTO Cups (name, mini_roster, signup_start_date, signup_end_date, category_id, chan_admin_id, chan_signups_id, chan_calendar_id, chan_stage_id, category_match_schedule_id, chan_match_index_id, maxi_roster, chan_results_id, ftw_cup_id) "
            "VALUES (%s, %d,  %s, %s,  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (name, mini_roster, signup_start_date, signup_end_date, category_id, chan_admin_id, chan_signups_id, chan_calendar_id, chan_stage_id, category_match_schedule_id, chan_match_index_id, maxi_roster, chan_results_id, ftw_cup_id))
        self.conn.commit()
        return self.cursor.lastrowid


    def get_cup(self, id=None, chan_admin_id=None):
        sql = "SELECT * FROM Cups WHERE "
        params = ()

        if id != None:
            sql += "id = %s "
            params += (id,)
        if chan_admin_id != None:
            if len(params) > 0:
                sql += "AND "
            sql += "chan_admin_id = %s "
            params += (chan_admin_id,)
        
        if len(params) == 0:
            return None

        self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def edit_cup(self, id, name=None, status=None, mini_roster=None, maxi_roster=None, signup_start_date=None, signup_end_date=None, signup_message_id=None):
        sql = "UPDATE Cups SET "
        params = ()

        if name != None:
            sql += "name = %s "
            params += (name,)
        if status != None:
            if len(params) > 0:
                sql += ", "
            sql += "status = %s "
            params += (status,)
        if mini_roster != None:
            if len(params) > 0:
                sql += ", "
            sql += "mini_roster = %s "
            params += (mini_roster,)
        if maxi_roster != None:
            if len(params) > 0:
                sql += ", "
            sql += "maxi_roster = %s "
            params += (maxi_roster,)
        if signup_start_date != None:
            if len(params) > 0:
                sql += ", "
            sql += "signup_start_date = %s "
            params += (signup_start_date,)
        if signup_end_date != None:
            if len(params) > 0:
                sql += ", "
            sql += "signup_end_date = %s "
            params += (signup_end_date,)
        if signup_message_id != None:
            if len(params) > 0:
                sql += ", "
            sql += "signup_message_id = %s "
            params += (signup_message_id,)
        if len(params) == 0:
            return
        sql += "WHERE id = %s"
        params += (id,)

        self.cursor.execute(sql, params)
        self.conn.commit()

    def get_all_cups(self, status):
        self.cursor.execute("SELECT * FROM Cups WHERE status = %s;", (status,))
        return self.cursor.fetchall()



#----Divisions--------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def create_division(self, div_number, cup_id, category_id, archive_category_id):
        self.cursor.execute("INSERT INTO Divisions (div_number, cup_id, category_id, archive_category_id) VALUES (%s, %s, %s, %s)", (div_number, cup_id, category_id, archive_category_id))
        self.conn.commit()


    def get_division(self, id=None, div_number=None, cup_id=None):
        sql = "SELECT * FROM Divisions WHERE "
        params = ()

        if id != None:
            sql += "id = %s "
            params += (id,)
        if div_number != None:
            if len(params) > 0:
                sql += "AND "
            sql += "div_number = %s "
            params += (div_number,)
        if cup_id != None:
            if len(params) > 0:
                sql += "AND "
            sql += "cup_id = %s "
            params += (cup_id,)
        
        if len(params) == 0:
            return None

        self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def delete_division(self, cup_id, div_number):
        self.cursor.execute("DELETE FROM Divisions WHERE cup_id=%s AND div_number=%s", (cup_id, div_number))
        self.conn.commit()

    def get_cup_divisions(self, cup_id):
        sql = "SELECT * FROM Divisions WHERE "
        params = ()

        if cup_id != None:
            sql += "cup_id = %s "
            params += (cup_id,)
        
        if len(params) == 0:
            return None

        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def edit_division(self, id, embed_id=None, category_id=None, archive_category_id=None):
        sql = "UPDATE Divisions SET "
        params = ()

        if format != None:
            sql += "format = %s "
            params += (format,)
        if embed_id != None:
            if len(params) > 0:
                sql += ", "
            sql += "embed_id = %s "
            params += (embed_id,)
        if category_id != None:
            if len(params) > 0:
                sql += ", "
            sql += "category_id = %s "
            params += (category_id,)
        if archive_category_id != None:
            if len(params) > 0:
                sql += ", "
            sql += "archive_category_id = %s "
            params += (archive_category_id,)
        if len(params) == 0:
            return
        sql += " WHERE id = %s"
        params += (id,)

        self.cursor.execute(sql, params)
        self.conn.commit()

    def get_all_divisions(self, cup_id):
        self.cursor.execute("SELECT * FROM Divisions WHERE cup_id=%s", (cup_id,))
        return self.cursor.fetchall()


#----Maps--------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def get_maps_gamemode(self, gamemode):
        self.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s", (gamemode.value,))
        return self.cursor.fetchall()

    def get_map(self, id):
        self.cursor.execute("SELECT * FROM Maps WHERE id = %s", (id,))
        return self.cursor.fetchone()

    
