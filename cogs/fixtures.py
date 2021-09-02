import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.dropmenus as dropmenus
import cogs.common.update as update
import time 
import datetime

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
                Button(style=ButtonStyle.blue, label="Schedule", custom_id=f"button_schedule_fixture"),
                Button(style=ButtonStyle.blue, label="Enter scores", custom_id=f"button_enter_scores"),
                Button(style=ButtonStyle.red, label="Delete fixture", custom_id=f"button_delete_fixture"),
            ]])
        elif interaction.component.id == "button_delete_fixture":
            await self.delete_fixture(interaction)
        elif interaction.component.id == "button_fixture_schedule":
            await self.schedule_fixture(interaction)
        elif interaction.component.id.startswith("button_accept_fixture_schedule_"):
            await self.schedule_accept(interaction)


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

        print(role_team1, role_team2)

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
        
        embed = embeds.fixture(self.bot, team1['id'], team2['id'], None, fixture_format)
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

    @commands.command() 
    async def schedule(self, ctx):
        # permissions
        if  not ctx.author.guild_permissions.manage_guild:
            return

        # Check args
        args = ctx.message.content[len("!schedule"):].split()
        if len(args) != 2:
            await ctx.channel.send(self.bot.quotes['cmdSchedule_error_args'])
            return

        # Check date
        date_checked, date = utils.check_date_format(args[0])
        if not date_checked:
            await ctx.channel.send(self.bot.quotes['cmdSchedule_error_date'])
            return

        # Check time 
        time_checked, time = utils.check_time_format(args[1])
        if not time_checked:
            await ctx.channel.send(self.bot.quotes['cmdSchedule_error_time'])
            return

        # Add time to date
        date= date.replace(hour= time.hour, minute = time.minute)

        # Update the date in the DB
        self.bot.cursor.execute("UPDATE Fixtures SET date=%s WHERE channel_id = %s", (date, str(ctx.channel.id)))
        self.bot.conn.commit()

        # Update the embed
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id = %s", (str(ctx.channel.id),))
        fixture_info = self.bot.cursor.fetchone()
        fixture_card = await ctx.channel.fetch_message(fixture_info['embed_id'])
        embed = embeds.fixture(self.bot, fixture_info['id'])
        await fixture_card.edit(embed=embed)

        await ctx.channel.send(self.bot.quotes['cmdSchedule_confirmation'])


    @commands.command() 
    async def pickban(self, ctx):
        # Check if there is not another operation happening for this fixture
        if ctx.channel.id in self.bot.fixtures_busy:
            return
        self.bot.fixtures_busy.append(ctx.channel.id)

        # Get fixture info
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id = %s", (str(ctx.channel.id),))
        fixture_info = self.bot.cursor.fetchone()

        # Get team1 and team2 info
        self.bot.cursor.execute("SELECT * FROM Teams WHERE tag=%s;", (fixture_info['team1'],))
        team1 = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE tag=%s;", (fixture_info['team2'],))
        team2 = self.bot.cursor.fetchone()
        clan_info_list = [team1, team2]

        # Find out who won the knife fight
        clan_choice = await embeds.team_list(self.bot, clan_info_list, "The team who won the knife fight decides which team starts to ban a map for TS first (the other team will ban a map for CTF first). Which team will start banning a **TS map**?", ctx)
        team_picking_ts_first = clan_choice
        if clan_choice['tag'] == team1['tag']:
            team_picking_ctf_first = team2
        else:
            team_picking_ctf_first = team1

        # TODO : Change maps to ban to 6 and 4 when there will be 7 maps for each mode
        # Check if BO2 (1 map per mode to pick) or BO5(2 maps per mode)
        if (fixture_info['format'] == 'BO2'):
            maps_to_ban = 2
            maps_to_pick = 1
        elif (fixture_info['format'] == 'BO5'):
            maps_to_ban = 1
            maps_to_pick = 2
        else:
            return

        # Get map lists
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s", ('TS',))
        ts_map_list = self.bot.cursor.fetchall()
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s", ('CTF',))
        ctf_map_list = self.bot.cursor.fetchall()

        # TODO: Check role and use text entry
        # Pick TS Maps
        ts_maps = []
        for i in range(maps_to_ban):
            banned_map = await embeds.map_list(self.bot, ts_map_list, "TS - TO BAN :x:", ctx)
            ts_map_list.remove(banned_map)
            await ctx.channel.send(f":x: Banned: ``{banned_map['name']}``")
        for i in range(maps_to_pick):
            picked_map = await embeds.map_list(self.bot, ts_map_list, "TS - TO PICK :white_check_mark:", ctx)
            ts_maps.append(picked_map['name'])
            ts_map_list.remove(picked_map)
            await ctx.channel.send(f":white_check_mark: Picked: ``{picked_map['name']}``")

        
        # Pick TS Map
        ctf_maps = []
        for i in range(maps_to_ban):
            banned_map = await embeds.map_list(self.bot, ctf_map_list, "CTF - TO BAN :x:", ctx)
            ctf_map_list.remove(banned_map)
            await ctx.channel.send(f":x: Banned: ``{banned_map['name']}``")
        for i in range(maps_to_pick):
            picked_map = await embeds.map_list(self.bot, ctf_map_list, "CTF - TO PICK :white_check_mark:", ctx)
            ctf_maps.append(picked_map['name'])
            ctf_map_list.remove(picked_map)
            await ctx.channel.send(f":white_check_mark: Picked: ``{picked_map['name']}``")

        # Remove busy status
        self.bot.fixtures_busy.remove(ctx.channel.id)

    async def schedule_fixture(self, interaction):
        # Check if user is busy
        if interaction.author.id in self.bot.users_busy:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='You are currently busy with another action with the bot, finish it and click again')
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
            await interaction.author.send("Enter the date (``DD/MM/YYYY``): \n*Type ``!cancel`` to cancel*")
            gamedate_msg = await self.bot.wait_for('message', check=check)
            gamedate = gamedate_msg.content.lower().strip()

            # Cancel 
            if gamedate == '!cancel':
                await interaction.author.send("Game scheduling canceled.")
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            game_date_checked, gamedate_formatted = utils.check_date_format(gamedate)

            if not game_date_checked:
                await interaction.author.send(self.bot.quotes['cmdCreateCup_error_date'])

        # Wait for game hour
        game_time_checked = False
        while not game_time_checked:
            await interaction.author.send("Enter the time of the game (``HH:MM``) in the **CEST** timezone. **\nUse 24-hour military time**, example: ``21:00``\n*Type ``!cancel`` to cancel*")
            gametime_msg = await self.bot.wait_for('message', check=check)
            gametime = gametime_msg.content.lower().strip()

            # Cancel 
            if gametime == '!cancel':
                await interaction.author.send("Game scheduling canceled.")
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            game_time_checked, gametime_formatted = utils.check_time_format(gametime)

            if not game_time_checked:
                await interaction.author.send("Wrong hour format, please check the instructions.")

        await interaction.author.send("Game scheduling successful.")

        gameschedule = datetime.datetime.combine(gamedate_formatted, gametime_formatted)
        print(gameschedule)


        await interaction.message.channel.send(f"<@&{other_team_info['role_id']}> The clan ``{team_info['name']}`` proposes to play the game on ``{gamedate}`` at ``{gametime} CEST``.", components=[[
            Button(style=ButtonStyle.green, label="Accept", custom_id=f"button_accept_fixture_schedule_{gameschedule}"),
            Button(style=ButtonStyle.red, label="Decline", custom_id=f"button_decline_fixture_schedule_{gameschedule}")
            ]])
        

def setup(bot):
    bot.add_cog(Fixtures(bot))
