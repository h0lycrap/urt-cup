from logging import disable
from operator import truediv
import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.dropmenus as dropmenus
import cogs.common.update as update
import time 
import datetime
import flag

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component

class Fixtures(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        user = discord.utils.get(self.guild.members, id=interaction.user.id)

        if interaction.component.id == "button_create_fixture":
            await self.create_fixture(interaction)
        elif interaction.component.id.startswith("button_create_fixtures_div"):
            await self.create_fixtures_division(interaction)
        elif interaction.component.id == "button_edit_fixture":
            # Check if the user is admin
            flawless_role = discord.utils.get(self.guild.roles, id=self.bot.role_flawless_crew_id)
            moderator_role = discord.utils.get(self.guild.roles, id=self.bot.role_moderator_id)
            if not flawless_role in user.roles and not moderator_role in user.roles:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Nice try, but you need to be an admin to press this.")
                return
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="What action do you want to perform?", components=[[
                Button(style=ButtonStyle.blue, label="Schedule", custom_id=f"button_schedule_fixture_admin"),
                Button(style=ButtonStyle.blue, label="Enter scores", custom_id=f"button_enter_scores"),
                Button(style=ButtonStyle.red, label="Delete fixture", custom_id=f"button_delete_fixture"),
            ]])
        elif interaction.component.id == "button_delete_fixture":
            await self.delete_fixture(interaction)
        elif interaction.component.id == "button_fixture_schedule":
            await self.schedule_fixture(interaction)
        elif interaction.component.id.startswith("button_accept_fixture_schedule_"):
            await self.schedule_accept(interaction)
            self.bot.async_loop.create_task(update.fixtures(self.bot))
        elif interaction.component.id.startswith("button_decline_fixture_schedule_"):
            await self.schedule_decline(interaction)
        elif interaction.component.id.startswith("button_schedule_fixture_admin"):
            await self.schedule_fixture_admin(interaction)
            self.bot.async_loop.create_task(update.fixtures(self.bot))
        elif interaction.component.id.startswith("button_fixture_startpickban"):
            await self.pickban_invitation(interaction)
        elif interaction.component.id.startswith("button_pickban_knifewon"):
            await self.pickban_knifewon(interaction)


    async def create_fixture(self, interaction):
        # Get which cup this is from 
        self.bot.cursor.execute("SELECT * FROM Cups WHERE chan_admin_id=%s;", (interaction.message.channel.id,))
        cup_toedit = self.bot.cursor.fetchone()

        # List clans signed up in the cup
        self.bot.cursor.execute("SELECT * FROM Signups WHERE cup_id = %s;", (cup_toedit['id'],))
        teams_signed_up  = self.bot.cursor.fetchall()

        if len(teams_signed_up) < 2:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="No team signed up for this cup")
            return

        # Get clan info list
        clan_info_list = []
        for team_signed_up in teams_signed_up:
            self.bot.cursor.execute("SELECT * FROM Teams WHERE id = %s;", (team_signed_up['team_id'],))
            clan_info = self.bot.cursor.fetchone()
            clan_info_list.append(clan_info)

        # First clan
        droplist_team1 = dropmenus.teams(clan_info_list, "Select a clan", "dropmenu_team1")
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="What is the first clan involved in this game?", components=droplist_team1)
        interaction_team1 = await self.bot.wait_for("select_option", check = lambda i: i.user.id == interaction.author.id and i.parent_component.id == "dropmenu_team1")
        team1 = clan_info_list[int(interaction_team1.component[0].value)]
        clan_info_list.remove(team1)

        # Second clan
        droplist_team2 = dropmenus.teams(clan_info_list, "Select a clan", "dropmenu_team2")
        await interaction_team1.respond(type=InteractionType.ChannelMessageWithSource, content="What is the second clan involved in this game?", components=droplist_team2)
        interaction_team2 = await self.bot.wait_for("select_option", check = lambda i: i.user.id == interaction.author.id and i.parent_component.id == "dropmenu_team2")
        team2 = clan_info_list[int(interaction_team2.component[0].value)]

        # Select format
        formats = ['BO1', 'BO2', 'BO3', 'BO5', 'BO7']
        droplist_format = dropmenus.formats(formats, "Select a format", "dropmenu_format")
        await interaction_team2.respond(type=InteractionType.ChannelMessageWithSource, content="What is the format of this game?", components=droplist_format)
        interaction_format = await self.bot.wait_for("select_option", check = lambda i: i.user.id == interaction.author.id and i.parent_component.id == "dropmenu_format")
        fixture_format = formats[int(interaction_format.component[0].value)]

        # Create the fixture
        await self.create_fixture_fun(team1, team2, cup_toedit, fixture_format)

        # Update fixtures
        await update.fixtures(self.bot)

        

    async def create_fixtures_division(self, interaction):
        # Get the division
        div_number = interaction.component.id.split("_")[-1]

        # Get cup info
        self.bot.cursor.execute("SELECT * FROM Cups WHERE chan_admin_id=%s", (interaction.message.channel.id,))
        cup_info = self.bot.cursor.fetchone()
        
        # Select format
        formats = ['BO1', 'BO2', 'BO3', 'BO5', 'BO7']
        droplist_format = dropmenus.formats(formats, "Select a format", "dropmenu_format")
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="What is the format of this game?", components=droplist_format)
        interaction_format = await self.bot.wait_for("select_option", check = lambda i: i.user.id == interaction.author.id and i.parent_component.id == "dropmenu_format")
        fixture_format = formats[int(interaction_format.component[0].value)]

        # Get all clans in div
        self.bot.cursor.execute("SELECT * FROM Signups s INNER JOIN Teams t ON s.team_id = t.id WHERE s.cup_id = %s and div_number=%s", (cup_info['id'], div_number))
        total_teams = self.bot.cursor.fetchall()

        if len(total_teams) < 2:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Not enough teams in this division.")
            return

        number_of_fixtures = len(total_teams) * (len(total_teams) - 1) / 2

        # Ask confirmation
        await interaction_format.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdCreateFixtures_confirmation'].format(number_of_fixtures=int(number_of_fixtures), div_number=div_number), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_createdivfixtures_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_createdivfixtures_no"),]])
        interaction_confirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction.author.id and i.component.id.startswith("button_createdivfixtures_"))

        if interaction_confirmation.component.id == 'button_createdivfixtures_no':
            await interaction_confirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdCreateFixtures_cancel'])
            return

        total_teams_copy = total_teams.copy()

        await interaction_confirmation.respond(type=InteractionType.ChannelMessageWithSource, content="Fixtures are being created, give it a few seconds to finish")
    
        if interaction_confirmation.component.id == 'button_createdivfixtures_yes':
            for team1 in total_teams:
                total_teams_copy.remove(team1)
                for team2 in total_teams_copy: 
                    await self.create_fixture_fun(team1, team2, cup_info, fixture_format)
                    # If too fast, the DB doesnt have time to update for some reason
                    #time.sleep(3)

        # Update fixtures
        await update.fixtures(self.bot)
        

    async def create_fixture_fun(self, team1, team2, cup_info, fixture_format):
        fixture_category = discord.utils.get(self.guild.channels, id=int(cup_info['category_match_schedule_id']))
        
        role_flawless_crew = discord.utils.get(self.guild.roles, id=int(self.bot.role_flawless_crew_id)) 
        role_moderator = discord.utils.get(self.guild.roles, id=int(self.bot.role_moderator_id))
        role_bot = discord.utils.get(self.guild.roles, id=int(self.bot.role_bot_id))

        # Get different roles that will have access to the channel
        role_team1 = discord.utils.get(self.guild.roles, id=int(team1['role_id'])) 
        role_team2 = discord.utils.get(self.guild.roles, id=int(team2['role_id'])) 

        # Set the permissions
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            role_bot: discord.PermissionOverwrite(read_messages=True),
            role_team1: discord.PermissionOverwrite(read_messages=True), 
            role_team2: discord.PermissionOverwrite(read_messages=True),
            role_flawless_crew: discord.PermissionOverwrite(read_messages=True),
            role_moderator: discord.PermissionOverwrite(read_messages=True)
        }

        # Create text channel 
        fixture_channel = await self.guild.create_text_channel(f"{cup_info['name']}┋{team1['tag']} vs {team2['tag']}", overwrites=overwrites, category=fixture_category)

        self.bot.cursor.execute("INSERT INTO Fixtures (cup_id, team1, team2, format, channel_id) VALUES (%d, %s, %s, %s, %s)", (cup_info['id'], team1['id'], team2['id'], fixture_format, str(fixture_channel.id)))
        self.bot.conn.commit()

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(content=f"The fixture for the cup ``{cup_info['name']}`` between ``{team1['tag']}`` and ``{team2['tag']}`` has been created.")

        # Send fixture card
        fixture_id = self.bot.cursor.lastrowid
        
        embed = embeds.fixture(bot=self.bot, team1_id=team1['id'], team2_id=team2['id'], date=None, format=fixture_format)
        fixture_card = await fixture_channel.send(embed=embed, components=[[
            Button(style=ButtonStyle.blue, label="Schedule game", custom_id=f"button_fixture_schedule"),
            Button(style=ButtonStyle.blue, label="Start pick & ban", custom_id=f"button_fixture_startpickban"),
            Button(style=ButtonStyle.grey, label="Admin Panel", custom_id=f"button_edit_fixture")
            ]])

        self.bot.cursor.execute("UPDATE Fixtures SET embed_id=%s WHERE id = %d", (str(fixture_card.id), fixture_id))
        self.bot.conn.commit()

    async def delete_fixture(self, interaction):
        # Get which feature to delete 
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture = self.bot.cursor.fetchone()

        # Ask confirmation
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeleteFixture_confirmation'], components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_deletefixture_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_deletefixture_no"),]])
        interaction_confirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction.author.id and i.component.id.startswith("button_deletefixture_"))

        if interaction_confirmation.component.id == 'button_deletefixture_no':
            await interaction_confirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEditFixture_cancel'])
            return
        
        if interaction_confirmation.component.id == 'button_deletefixture_yes':
            # Delete channel
            await interaction.message.channel.delete()

            # Delete fixture in DV
            self.bot.cursor.execute("DELETE FROM Fixtures WHERE id=%s", (fixture['id'],))
            self.bot.conn.commit()


            # TODO WHEN PLAYER IMPLEMENTED DELETE HERE TOO 

    async def pickban_invitation(self, interaction):
        # Check if fixture busy
        if interaction.message.channel.id in self.bot.fixtures_busy:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_busy'])
            return

        # Get  feature  
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Check if the game is scheduled and not finished
        if not fixture_info['status']:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_notscheduled'])
            return
        elif fixture_info['status'] != 1:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_finished'])
            return

        #Flag busy
        self.bot.fixtures_busy.append(interaction.message.channel.id)

        # Get clans info
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
        team1_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
        team2_info = self.bot.cursor.fetchone()

        # Check if we are match day
        gamedate = datetime.date.fromisoformat(fixture_info['date'].split()[0])
        if gamedate != datetime.datetime.now().date():
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_gamedate'])
            self.bot.fixtures_busy.remove(interaction.message.channel.id)
            return

        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_prompt'], components=[[
                Button(style=ButtonStyle.blue, label=f"{team1_info['tag']}", emoji=flag.flagize(team1_info['country']), custom_id=f"button_pickban_knifewon_{team1_info['id']}"),
                Button(style=ButtonStyle.blue, label=f"{team2_info['tag']}", emoji=flag.flagize(team2_info['country']), custom_id=f"button_pickban_knifewon_{team2_info['id']}")]], ephemeral=False)


    async def pickban_knifewon(self, interaction):
        # Get  feature  
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Get clans info
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
        team1_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
        team2_info = self.bot.cursor.fetchone()

        # Get the team of the clicker
        user = discord.utils.get(self.guild.members, id=interaction.user.id)
        team1_role = discord.utils.get(self.guild.roles, id= int(team1_info['role_id']))
        team2_role = discord.utils.get(self.guild.roles, id= int(team2_info['role_id']))
        if team1_role in user.roles:
            team_click = team1_info
            otherteam_click = team2_info
        elif team2_role in user.roles:
            team_click = team2_info
            otherteam_click = team1_info
        else:
            print(f"ERROR: can't retrieve clicking team for fixture {fixture_info['id']}")  
            self.bot.fixtures_busy.remove(interaction.message.channel.id)
            return  

        # Check if the team was clicked before
        team_clicked_before_id = interaction.component.id.split("_")[-2]
        both_team_agreed = False
        if team_clicked_before_id == str(otherteam_click['id']):
            both_team_agreed = True

        # Get team from button
        team_id = interaction.component.id.split("_")[-1]
        if team_id == str(team1_info['id']):
            team_button = team1_info
            other_team_button = team2_info
            team1_button_style = ButtonStyle.green
            team2_button_style = ButtonStyle.blue
            if both_team_agreed:
                team1_button_label = f"{team1_info['tag']}"
            else:
                team1_button_label = f"{team1_info['tag']} (claimed by {team_click['tag']})"
            team2_button_label = f"{team2_info['tag']}"
            team1_button_id = f"button_pickban_knifewon_{team_click['id']}_{team1_info['id']}"
            team2_button_id = f"button_pickban_knifewon_{team2_info['id']}"
            
        elif team_id == str(team2_info['id']):
            team_button = team2_info
            other_team_button = team1_info
            team1_button_style = ButtonStyle.blue
            team2_button_style = ButtonStyle.green
            if both_team_agreed:
                team2_button_label = f"{team2_info['tag']}"
            else:
                team2_button_label = f"{team2_info['tag']} (claimed by {team_click['tag']})"
            team1_button_label = f"{team1_info['tag']}"
            team2_button_id = f"button_pickban_knifewon_{team_click['id']}_{team2_info['id']}"
            team1_button_id = f"button_pickban_knifewon_{team1_info['id']}"
        else:
            print(f"ERROR: cant retrieve team from button for fixture {fixture_info['id']}")
            self.bot.fixtures_busy.remove(interaction.message.channel.id)
            return 

        await interaction.message.edit(self.bot.quotes['cmdPickBanInvitation_prompt'], components=[[
                Button(style=team1_button_style, label=team1_button_label, emoji=flag.flagize(team1_info['country']), custom_id=team1_button_id, disabled=both_team_agreed),
                Button(style=team2_button_style, label=team2_button_label, emoji=flag.flagize(team2_info['country']), custom_id=team2_button_id, disabled=both_team_agreed)]])


        await interaction.respond(type=6)

        if both_team_agreed:
            if (fixture_info['format'] == 'BO2'):
                await self.pickban_bo2(fixture_info, team_button, other_team_button, interaction.message.channel)

            # TODO Implement BO3 and BO5

    # Team 1 won the knife fight
    async def pickban_bo2(self, fixture_info, team1, team2, channel):

        # Get map lists
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s", ('TS',))
        ts_map_list = self.bot.cursor.fetchall()
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s", ('CTF',))
        ctf_map_list = self.bot.cursor.fetchall()

        # Get team roles
        team1_role = discord.utils.get(self.guild.roles, id= int(team1['role_id']))
        team2_role = discord.utils.get(self.guild.roles, id= int(team2['role_id']))


        # Ask winning team what map advantage they want 
        mapadvantage_msg = await channel.send(self.bot.quotes['cmdPickBan_gamemode_advantage_prompt'].format(team1_role_id=team1_role.id), components=[[
            Button(style=ButtonStyle.blue, label="TS", custom_id="button_gamemode_ban_advantage_ts"),
            Button(style=ButtonStyle.blue, label="CTF", custom_id="button_gamemode_ban_advantage_ctf")
        ]])

        gamemode_advantage_check = False
        while not gamemode_advantage_check:
            interaction_gamemodeadvantage = await self.bot.wait_for("button_click", check = lambda i: i.component.id.startswith("button_gamemode_ban_advantage"))
            user_clicking = discord.utils.get(self.guild.members, id=interaction_gamemodeadvantage.author.id)
            if team1_role in user_clicking.roles:
                gamemode_advantage_check = True
            else:
                await interaction_gamemodeadvantage.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=team1['name']))

        if interaction_gamemodeadvantage.component.id == 'button_gamemode_ban_advantage_ts':
            await mapadvantage_msg.edit(self.bot.quotes['cmdPickBan_gamemode_advantage_prompt'].format(team1_role_id=team1_role.id), components=[[
                Button(style=ButtonStyle.green, label="TS", custom_id="button_gamemode_ban_advantage_ts", disabled=True),
                Button(style=ButtonStyle.blue, label="CTF", custom_id="button_gamemode_ban_advantage_ctf", disabled=True)
            ]])
            mapadvantage_ts = team1
            mapadvantage_ctf = team2

        
        if interaction_gamemodeadvantage.component.id == 'button_gamemode_ban_advantage_ctf':
            await mapadvantage_msg.edit(self.bot.quotes['cmdPickBan_gamemode_advantage_prompt'].format(team1_role_id=team1_role.id), components=[[
                Button(style=ButtonStyle.blue, label="TS", custom_id="button_gamemode_ban_advantage_ts", disabled=True),
                Button(style=ButtonStyle.green, label="CTF", custom_id="button_gamemode_ban_advantage_ctf", disabled=True)
            ]])
            mapadvantage_ts = team2
            mapadvantage_ctf = team1

        await interaction_gamemodeadvantage.respond(type=6)
        ts_map = await self.banuntil2(mapadvantage_ctf, mapadvantage_ts, channel, "TS")
        ctf_map = await self.banuntil2(mapadvantage_ctf, mapadvantage_ts, channel, "CTF")

        # Add maps to DB
        self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], ts_map['id']))
        self.bot.conn.commit()
        self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], ctf_map['id']))
        self.bot.conn.commit()

        # Set fixture to on-going
        self.bot.cursor.execute("UPDATE Fixtures set status = 2 WHERE id=%s", (fixture_info['id'],))
        self.bot.conn.commit()

        # Remove busy status
        self.bot.fixtures_busy.remove(channel.id)

        # Notify
        await channel.send(self.bot.quotes['cmdPickBan_bo2_end'].format(teamname=team1['name'], tsmap=ts_map['name'], ctfmap=ctf_map['name']))

        # Update fixtures
        self.bot.async_loop.create_task(update.fixtures(self.bot))


    async def banuntil2(self, mapadvantage_ctf, mapadvantage_ts, channel, gamemode):
        if gamemode == "TS":
            # Start TS pick and ban
            await channel.send(self.bot.quotes['cmdPickBan_TS_intro'].format(mapadvantage_ctf_role_id=mapadvantage_ctf['role_id'], mapadvantage_ts_role_id=mapadvantage_ts['role_id']))
            # The ctf advantage team starts to ban
            team_toban = mapadvantage_ctf
        else:
            # Start CTF pick and ban
            await channel.send(self.bot.quotes['cmdPickBan_CTF_intro'].format(mapadvantage_ctf_role_id=mapadvantage_ctf['role_id'], mapadvantage_ts_role_id=mapadvantage_ts['role_id']))
            # The ctf advantage team starts to ban
            team_toban = mapadvantage_ts

        # Get maps
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s;", (gamemode,))
        maps = self.bot.cursor.fetchall()
        maps.sort(key=lambda x: x['name'])

        embed_title = f"{gamemode} Maps"

        # Send embeds with the remaining maps
        map_embed = embeds.map_list(maps, embed_title)
        await channel.send(embed=map_embed)

        # Ban until 2 maps are left
        while len(maps) > 2:
            # Prompt the ban
            pickban_dropmenu = dropmenus.maps(maps, "pickban_ts")
            pickban_prompt_msg = await channel.send(self.bot.quotes['cmdPickBan_prompt_ban'].format(team_role_id=team_toban['role_id']), components=pickban_dropmenu)

            # Get banning team role
            team_toban_role = discord.utils.get(self.guild.roles, id= int(team_toban['role_id']))

            ban_check = False
            while not ban_check:
                interaction_ban = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_ts")
                map_toban = maps[int(interaction_ban.component[0].value)]
                user_clicking = discord.utils.get(self.guild.members, id=interaction_ban.author.id)
                if team_toban_role in user_clicking.roles:
                    ban_check = True
                else:
                    await interaction_ban.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=team_toban['name']))

            await interaction_ban.respond(type=6)
            # Ban the map
            maps.remove(map_toban)

            # Edit embed and delete prompt
            await channel.send(self.bot.quotes['cmdPickBan_ban_success'].format(mapname=map_toban['name']))
            map_embed = embeds.map_list(maps, embed_title)
            await channel.send(embed=map_embed)
            await pickban_prompt_msg.delete()

            # Switch banning team
            if team_toban == mapadvantage_ctf:
                team_toban = mapadvantage_ts
            else:
                team_toban = mapadvantage_ctf

        # Pick between the last two maps
        # Prompt the pick
        pickban_dropmenu = dropmenus.maps(maps, "pickban_ts")

        # Get banning team role
        if gamemode == "TS":
            pickban_prompt_msg = await channel.send(self.bot.quotes['cmdPickBan_prompt_pick'].format(team_role_id=mapadvantage_ts['role_id']), components=pickban_dropmenu)
            team_topick_role = discord.utils.get(self.guild.roles, id= int(mapadvantage_ts['role_id']))
        else:
            pickban_prompt_msg = await channel.send(self.bot.quotes['cmdPickBan_prompt_pick'].format(team_role_id=mapadvantage_ctf['role_id']), components=pickban_dropmenu)
            team_topick_role = discord.utils.get(self.guild.roles, id= int(mapadvantage_ctf['role_id']))

        pick_check = False
        while not pick_check:
            interaction_pick = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_ts")
            picked_map = maps[int(interaction_pick.component[0].value)]
            user_clicking = discord.utils.get(self.guild.members, id=interaction_pick.author.id)
            if team_topick_role in user_clicking.roles:
                pick_check = True
            else:
                if gamemode == "TS":
                    await interaction_pick.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=mapadvantage_ts['name']))
                else:
                    await interaction_pick.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=mapadvantage_ctf['name']))

        await interaction_pick.respond(type=6)

        # Delete prompt
        await pickban_prompt_msg.delete()

        await channel.send(self.bot.quotes['cmdPickBan_pick_success'].format(mapname=picked_map['name'], gamemode=gamemode))

        return picked_map    

    async def schedule_fixture(self, interaction):
        # Check if user is busy
        if interaction.author.id in self.bot.users_busy:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdErrorBusy'])
            return

        # Flag as busy
        self.bot.users_busy.append(interaction.author.id)
                
        # Get fixture info
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Get clan info
        self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id=%s", (interaction.author.id,))
        user_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Roster WHERE player_id=%s and (team_id=%s or team_id=%s)", (user_info['id'], fixture_info['team1'], fixture_info['team2']))
        roster_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (roster_info['team_id'],))
        team_info = self.bot.cursor.fetchone()

        # Get other team info
        if int(fixture_info['team1']) == int(team_info['id']):
            self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
            other_team_info = self.bot.cursor.fetchone()
        elif int(fixture_info['team2']) == int(team_info['id']):
            self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
            other_team_info = self.bot.cursor.fetchone()
        else:
            self.bot.users_busy.remove(interaction.author.id)
            print("problem", team_info['id'], fixture_info['team1'], fixture_info['team2'])
            return



        # Check if match can be scheduled
        if not fixture_info['status'] == None and not int(fixture_info['status']) == 1:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"Error, match can't be scheduled")
            self.bot.users_busy.remove(interaction.author.id)
            return

        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"Check dms!")

        def check(m):
            return m.author == interaction.author and m.guild == None

        # Wait for game date
        game_date_checked = False
        while not game_date_checked:
            await interaction.author.send(self.bot.quotes['cmdSchedule_date_prompt'])
            gamedate_msg = await self.bot.wait_for('message', check=check)
            gamedate = gamedate_msg.content.lower().strip()

            # Cancel 
            if gamedate == '!cancel':
                await interaction.author.send(self.bot.quotes['cmdSchedule_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            game_date_checked, gamedate_formatted = utils.check_date_format(gamedate)

            if not game_date_checked:
                await interaction.author.send(self.bot.quotes['cmdCreateCup_error_date'])

        # Wait for game hour
        game_time_checked = False
        while not game_time_checked:
            await interaction.author.send(self.bot.quotes['cmdSchedule_time_prompt'])
            gametime_msg = await self.bot.wait_for('message', check=check)
            gametime = gametime_msg.content.lower().strip()

            # Cancel 
            if gametime == '!cancel':
                await interaction.author.send(self.bot.quotes['cmdSchedule_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            game_time_checked, gametime_formatted = utils.check_time_format(gametime)

            if not game_time_checked:
                await interaction.author.send(self.bot.quotes['cmdSchedule_error_time'])

        await interaction.author.send(self.bot.quotes['cmdSchedule_success'])

        # Remove busy status
        self.bot.users_busy.remove(interaction.author.id)

        gameschedule = datetime.datetime.combine(gamedate_formatted, gametime_formatted)


        await interaction.message.channel.send(self.bot.quotes['cmdSchedule_invitation'].format(roleid=other_team_info['role_id'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime), components=[[
            Button(style=ButtonStyle.green, label="Accept", custom_id=f"button_accept_fixture_schedule_{other_team_info['id']}_{gameschedule}"),
            Button(style=ButtonStyle.red, label="Decline", custom_id=f"button_decline_fixture_schedule_{other_team_info['id']}_{gameschedule}")
            ]])

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSchedule_invitation_log'].format(otherteamname=other_team_info['name'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime))


    async def schedule_fixture_admin(self, interaction):
        # Check if user is busy
        if interaction.author.id in self.bot.users_busy:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdErrorBusy'])
            return

        # Flag as busy
        self.bot.users_busy.append(interaction.author.id)
                
        # Get fixture info
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Get clans info
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
        team_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
        other_team_info = self.bot.cursor.fetchone()

        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"Check dms!")

        def check(m):
            return m.author == interaction.author and m.guild == None

        # Wait for game date
        game_date_checked = False
        while not game_date_checked:
            await interaction.author.send(self.bot.quotes['cmdSchedule_date_prompt'])
            gamedate_msg = await self.bot.wait_for('message', check=check)
            gamedate = gamedate_msg.content.lower().strip()

            # Cancel 
            if gamedate == '!cancel':
                await interaction.author.send(self.bot.quotes['cmdSchedule_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            game_date_checked, gamedate_formatted = utils.check_date_format(gamedate)

            if not game_date_checked:
                await interaction.author.send(self.bot.quotes['cmdCreateCup_error_date'])

        # Wait for game hour
        game_time_checked = False
        while not game_time_checked:
            await interaction.author.send(self.bot.quotes['cmdSchedule_time_prompt'])
            gametime_msg = await self.bot.wait_for('message', check=check)
            gametime = gametime_msg.content.lower().strip()

            # Cancel 
            if gametime == '!cancel':
                await interaction.author.send(self.bot.quotes['cmdSchedule_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            game_time_checked, gametime_formatted = utils.check_time_format(gametime)

            if not game_time_checked:
                await interaction.author.send(self.bot.quotes['cmdSchedule_error_time'])

        await interaction.author.send(self.bot.quotes['cmdSchedule_admin_success'])

        # Remove busy status
        self.bot.users_busy.remove(interaction.author.id)

        gameschedule = datetime.datetime.combine(gamedate_formatted, gametime_formatted)
        gamedate_str = str(gameschedule)

        # Update in DB
        self.bot.cursor.execute("UPDATE Fixtures set date=%s WHERE id=%s", (gamedate_str, fixture_info['id']))
        self.bot.conn.commit()
        self.bot.cursor.execute("UPDATE Fixtures set status=1 WHERE id=%s", (fixture_info['id'],))
        self.bot.conn.commit()

        # Notify
        await interaction.message.channel.send(self.bot.quotes['cmdSchedule_accepted_success'].format(otherroleid=other_team_info['role_id'], roleid=team_info['role_id'], gamedate=gamedate, gametime=gametime))

        # Update embed
        embed_message = await interaction.channel.fetch_message(fixture_info['embed_id'])
        fixture_embed = embeds.fixture(self.bot, fixture_id=fixture_info['id'])
        await embed_message.edit(embed=fixture_embed)

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSchedule_accepted_log'].format(otherteamname=other_team_info['name'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime))

    async def schedule_accept(self, interaction):
        # Get fixture info
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Get clan info
        self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id=%s", (interaction.author.id,))
        user_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Roster WHERE player_id=%s and (team_id=%s or team_id=%s)", (user_info['id'], fixture_info['team1'], fixture_info['team2']))
        roster_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (roster_info['team_id'],))
        team_info = self.bot.cursor.fetchone()

        # Get other team info
        if int(fixture_info['team1']) == int(team_info['id']):
            self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
            other_team_info = self.bot.cursor.fetchone()
        elif int(fixture_info['team2']) == int(team_info['id']):
            self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
            other_team_info = self.bot.cursor.fetchone()
        else:
            self.bot.users_busy.remove(interaction.author.id)
            print("problem", team_info['id'], fixture_info['team1'], fixture_info['team2'])
            return

        # Get fixture date
        gamedate_str = interaction.component.id.split("_")[-1]
        gamedate = datetime.date.fromisoformat(gamedate_str.split()[0])
        gametime = datetime.time.fromisoformat(gamedate_str.split()[1])
        gameschedule = datetime.datetime.combine(gamedate, gametime)
        
        # Check if the other team clicked
        invited_team_id = interaction.component.id.split("_")[-2]
        print(team_info['id'], invited_team_id)
        if int(team_info['id']) != int(invited_team_id):
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSchedule_error_notinteam'].format(otherteamname=other_team_info['name']))
            return
        
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSchedule_accepted'])

        # Update in DB
        self.bot.cursor.execute("UPDATE Fixtures set date=%s WHERE id=%s", (gamedate_str, fixture_info['id']))
        self.bot.conn.commit()
        self.bot.cursor.execute("UPDATE Fixtures set status=1 WHERE id=%s", (fixture_info['id'],))
        self.bot.conn.commit()

        # Notify
        await interaction.message.channel.send(self.bot.quotes['cmdSchedule_accepted_success'].format(otherroleid=other_team_info['role_id'], roleid=team_info['role_id'], gamedate=gamedate, gametime=gametime))

        await interaction.message.delete()

        # Update embed
        embed_message = await interaction.channel.fetch_message(fixture_info['embed_id'])
        fixture_embed = embeds.fixture(self.bot, fixture_id=fixture_info['id'])
        await embed_message.edit(embed=fixture_embed)

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSchedule_accepted_log'].format(otherteamname=other_team_info['name'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime))

    async def schedule_decline(self, interaction):
        # Get fixture info
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Get clan info
        self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id=%s", (interaction.author.id,))
        user_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Roster WHERE player_id=%s and (team_id=%s or team_id=%s)", (user_info['id'], fixture_info['team1'], fixture_info['team2']))
        roster_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (roster_info['team_id'],))
        team_info = self.bot.cursor.fetchone()

        # Get other team info
        if int(fixture_info['team1']) == int(team_info['id']):
            self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
            other_team_info = self.bot.cursor.fetchone()
        elif int(fixture_info['team2']) == int(team_info['id']):
            self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
            other_team_info = self.bot.cursor.fetchone()
        else:
            self.bot.users_busy.remove(interaction.author.id)
            print("problem", team_info['id'], fixture_info['team1'], fixture_info['team2'])
            return

        # Get fixture date
        gamedate_str = interaction.component.id.split("_")[-1]
        gamedate = datetime.date.fromisoformat(gamedate_str.split()[0])
        gametime = datetime.time.fromisoformat(gamedate_str.split()[1])
        gameschedule = datetime.datetime.combine(gamedate, gametime)
        
        # Check if the other team clicked
        invited_team_id = interaction.component.id.split("_")[-2]
        print(team_info['id'], invited_team_id)
        if int(team_info['id']) != int(invited_team_id):
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSchedule_error_notinteam'].format(otherteamname=other_team_info['name']))
            return
        
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSchedule_declined'])

        # Notify
        await interaction.message.channel.send(self.bot.quotes['cmdSchedule_declined_success'].format(otherroleid=other_team_info['role_id'], gamedate=gamedate, gametime=gametime))

        await interaction.message.delete()

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSchedule_declined_log'].format(otherteamname=other_team_info['name'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime))


def setup(bot):
    bot.add_cog(Fixtures(bot))
