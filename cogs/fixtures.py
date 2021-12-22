import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.dropmenus as dropmenus
import cogs.common.update as update
import datetime
import flag

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component

from ftwgl import FTWClient, MatchType


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
                Button(style=ButtonStyle.blue, label="Change Maps", custom_id=f"button_change_map_fixture_admin"),
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
        elif interaction.component.id.startswith("button_pickban_draw_knifewon"):
            await self.pickban_draw_knifewon(interaction)
        elif interaction.component.id.startswith("button_pickban_draw"):
            await self.pickban_draw_invitation(interaction)
        elif interaction.component.id.startswith("button_enter_scores"):
            await self.enter_scores(interaction)
            self.bot.async_loop.create_task(update.fixtures(self.bot))
            self.bot.async_loop.create_task(update.signups(self.bot))
        elif interaction.component.id.startswith("button_change_map_fixture_admin"):
            await self.change_map_fixture_admin(interaction)

    async def create_fixture(self, interaction):
        # Get which cup this is from 
        self.bot.cursor.execute("SELECT * FROM Cups WHERE chan_admin_id=%s;", (interaction.message.channel.id,))
        cup_toedit = self.bot.cursor.fetchone()

        # List clans signed up in the cup
        self.bot.cursor.execute("SELECT * FROM Signups WHERE cup_id = %s;", (cup_toedit['id'],))
        teams_signed_up  = self.bot.cursor.fetchall()

        # Get division 1 by default
        self.bot.cursor.execute("SELECT * FROM Divisions WHERE cup_id = %s AND div_number=1;", (cup_toedit['id'],))
        div_info  = self.bot.cursor.fetchone()

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
        formats = ['BO2', 'BO3', 'BO5']
        droplist_format = dropmenus.formats(formats, "Select a format", "dropmenu_format")
        await interaction_team2.respond(type=InteractionType.ChannelMessageWithSource, content="What is the format of this game?", components=droplist_format)
        interaction_format = await self.bot.wait_for("select_option", check = lambda i: i.user.id == interaction.author.id and i.parent_component.id == "dropmenu_format")
        fixture_format = formats[int(interaction_format.component[0].value)]

        # Select title
        titles = ['Quarter Finals', 'Semi Finals', 'Bronze Final', 'Final', 'Other']
        droplist_title= dropmenus.formats(titles, "Select a title", "dropmenu_title")
        await interaction_format.respond(type=InteractionType.ChannelMessageWithSource, content="What is the title of this game?", components=droplist_title)
        interaction_title = await self.bot.wait_for("select_option", check = lambda i: i.user.id == interaction.author.id and i.parent_component.id == "dropmenu_title")
        fixture_title = titles[int(interaction_title.component[0].value)]

        await interaction_title.respond(type=InteractionType.ChannelMessageWithSource, content="Creating fixture")

        # Create the fixture
        await self.create_fixture_fun(team1, team2, cup_toedit, fixture_format, div_info, fixture_title)

        # Update fixtures
        await update.fixtures(self.bot)

        

    async def create_fixtures_division(self, interaction):
        # Get the division
        div_number = interaction.component.id.split("_")[-1]

        # Get cup info
        self.bot.cursor.execute("SELECT * FROM Cups WHERE chan_admin_id=%s", (interaction.message.channel.id,))
        cup_info = self.bot.cursor.fetchone()

        # Get div info
        self.bot.cursor.execute("SELECT * FROM Divisions WHERE cup_id=%s and div_number=%s", (cup_info['id'], div_number))
        div_info = self.bot.cursor.fetchone()
        
        # Select format
        formats = ['BO2'] #['BO1', 'BO2', 'BO3', 'BO5', 'BO7']
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
        total_teams_copy = total_teams_copy[::-1]

        await interaction_confirmation.respond(type=InteractionType.ChannelMessageWithSource, content="Fixtures are being created, give it a few seconds to finish")
    
        if interaction_confirmation.component.id == 'button_createdivfixtures_yes':
            
            # Add a fake team if there is an off number of teams 
            if len(total_teams) % 2:
                total_teams.append('Day off')
            n = len(total_teams)


            for round in range(1, n):
                # Create new category for the other half # Cant have more than 100 games 
                if len(total_teams) * (len(total_teams) - 1) / 2 > 50 and  round == n // 2 + 1:
                    # Rename first category
                    match_category = discord.utils.get(self.guild.categories, id=int(div_info['category_id']))
                    await match_category.edit(name=f"\U0001F4C5┋{cup_info['name']}┋D{div_number} Round 1->{n // 2}")

                    # Create new category
                    new_match_category = await self.guild.create_category_channel(f"\U0001F4C5┋{cup_info['name']}┋D{div_number} Round {n // 2 + 1}->{n-1}")

                    # Update DB
                    self.bot.cursor.execute("UPDATE Divisions SET category_id = %s WHERE id=%s", (new_match_category.id, div_info['id']))
                    self.bot.conn.commit()
                    div_info['category_id'] = new_match_category.id

                for i in range(int(n / 2)):
                    # Discard if it is against the fake team
                    if total_teams[i] == 'Day off' or total_teams[n - 1 - i] == 'Day off':
                        continue

                    # Create fixture
                    await self.create_fixture_fun(total_teams[i], total_teams[n - 1 - i], cup_info, fixture_format, div_info, f"Round {round}")

                # Rotate
                total_teams.insert(1, total_teams.pop())


            '''
            for i in range(len(total_teams)):
                print('Round ', i + 1)
                total_teams_copy = total_teams_copy[1:] + [total_teams_copy[0]]
                for j in range(len(total_teams) // 2):
                    print(total_teams[j]['tag'], total_teams_copy[j]['tag'])
                
                
            
            for team1 in total_teams:
                total_teams_copy.remove(team1)
                for team2 in total_teams_copy: 
                    await self.create_fixture_fun(team1, team2, cup_info, fixture_format)
                    # If too fast, the DB doesnt have time to update for some reason
                    #time.sleep(3)
            '''

        # Update fixtures
        await update.fixtures(self.bot)
        

    async def create_fixture_fun(self, team1, team2, cup_info, fixture_format, div_info, title):
        fixture_category = discord.utils.get(self.guild.channels, id=int(div_info['category_id']))
        
        role_flawless_crew = discord.utils.get(self.guild.roles, id=int(self.bot.role_flawless_crew_id)) 
        role_moderator = discord.utils.get(self.guild.roles, id=int(self.bot.role_moderator_id))
        role_streamer = discord.utils.get(self.guild.roles, id=int(self.bot.role_streamer_id))
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
            role_moderator: discord.PermissionOverwrite(read_messages=True),
            role_streamer: discord.PermissionOverwrite(read_messages=True)
        }

        # Create text channel 
        fixture_channel = await self.guild.create_text_channel(f"{title}┋{team1['tag']} vs {team2['tag']}", overwrites=overwrites, category=fixture_category)

        def title_to_ftw_match_type(input: str) -> MatchType:
            if input == 'Quarter Finals':
                return MatchType.quarter_final
            elif input == 'Semi Finals':
                return MatchType.semi_final
            elif input == 'Bronze Final':
                return MatchType.silver_final
            elif input == 'Final':
                return MatchType.grand_final
            else:
                return MatchType.group

        ftw_client: FTWClient = self.bot.ftw
        ftw_match_id = await ftw_client.match_create(
            cup_id=cup_info['ftw_cup_id'],
            team_ids=[team1['ftw_team_id'], team2['ftw_team_id']],
            best_of=int(fixture_format[2]),
            match_type=title_to_ftw_match_type(title),
            match_date=None
        )

        self.bot.cursor.execute("INSERT INTO Fixtures (cup_id, team1, team2, format, channel_id, ftw_match_id) VALUES (%d, %s, %s, %s, %s, %s)", (cup_info['id'], team1['id'], team2['id'], fixture_format, str(fixture_channel.id), ftw_match_id))
        self.bot.conn.commit()

        # Print on the log channel
        log_channel = discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(content=f"The fixture for the cup ``{cup_info['name']}`` between ``{team1['tag']}`` and ``{team2['tag']}`` has been created.")

        # Send fixture card
        fixture_id = self.bot.cursor.lastrowid
        
        embed, components = await embeds.fixture(bot=self.bot, team1_id=team1['id'], team2_id=team2['id'], date=None, format=fixture_format)
        fixture_card = await fixture_channel.send(embed=embed, components=components)

        self.bot.cursor.execute("UPDATE Fixtures SET embed_id=%s WHERE id = %d", (str(fixture_card.id), fixture_id))
        self.bot.conn.commit()

    # print the fixture card if too high in the messages
    @commands.command()
    async def fixture(self, ctx):
        # Find fixture from channel
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s;", (ctx.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Do nothing if this isnt a fixture channel
        if not fixture_info:
            return

        # Send card
        embed, components = await embeds.fixture(self.bot, fixture_id=fixture_info['id'])
        await ctx.send(embed=embed, components=components)

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
            if (fixture_info['format'] == 'BO2' or fixture_info['format'] == 'BO3'):
                await self.pickban_bo2(fixture_info, team_button, other_team_button, interaction.message.channel)

            if (fixture_info['format'] == 'BO5'):
                await self.pickban_bo5(fixture_info, team_button, other_team_button, interaction.message.channel)

            if (fixture_info['format'] == 'BO3' or fixture_info['format'] == 'BO5'):
                await interaction.message.channel.send(self.bot.quotes['cmdPickBan_Prompt_draw'], components=[[Button(style=ButtonStyle.blue, label="Draw", custom_id="button_pickban_draw")]])

        # Update embed
        embed_message = await interaction.channel.fetch_message(fixture_info['embed_id'])
        fixture_embed, components = await embeds.fixture(self.bot, fixture_id=fixture_info['id'])
        await embed_message.edit(embed=fixture_embed, components=components)

    async def pickban_draw_invitation(self, interaction):
        # Check if fixture busy
        if interaction.message.channel.id in self.bot.fixtures_busy:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_busy'])
            return

        # Get  feature  
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Check if the game is on going
        if not fixture_info['status']:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_notscheduled'])
            return
        elif fixture_info['status'] != 2:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_finished'])
            return

        #Flag busy
        self.bot.fixtures_busy.append(interaction.message.channel.id)

        # Get clans info
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
        team1_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
        team2_info = self.bot.cursor.fetchone()

        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanDrawInvitation_prompt'], components=[[
                Button(style=ButtonStyle.blue, label=f"{team1_info['tag']}", emoji=flag.flagize(team1_info['country']), custom_id=f"button_pickban_draw_knifewon_{team1_info['id']}"),
                Button(style=ButtonStyle.blue, label=f"{team2_info['tag']}", emoji=flag.flagize(team2_info['country']), custom_id=f"button_pickban_draw_knifewon_{team2_info['id']}")]], ephemeral=False)


    async def pickban_draw_knifewon(self, interaction):
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
            team1_button_id = f"button_pickban_draw_knifewon_{team_click['id']}_{team1_info['id']}"
            team2_button_id = f"button_pickban_draw_knifewon_{team2_info['id']}"
            
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
            team2_button_id = f"button_pickban_draw_knifewon_{team_click['id']}_{team2_info['id']}"
            team1_button_id = f"button_pickban_draw_knifewon_{team1_info['id']}"
        else:
            print(f"ERROR: cant retrieve team from button for fixture {fixture_info['id']}")
            self.bot.fixtures_busy.remove(interaction.message.channel.id)
            return 

        await interaction.message.edit(self.bot.quotes['cmdPickBanDrawInvitation_prompt'], components=[[
                Button(style=team1_button_style, label=team1_button_label, emoji=flag.flagize(team1_info['country']), custom_id=team1_button_id, disabled=both_team_agreed),
                Button(style=team2_button_style, label=team2_button_label, emoji=flag.flagize(team2_info['country']), custom_id=team2_button_id, disabled=both_team_agreed)]])

        await interaction.respond(type=6)

        if both_team_agreed:
            await self.pickban_draw(fixture_info, team_button, other_team_button, interaction.message.channel)


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

    async def pickban_bo5(self, fixture_info, team1, team2, channel):

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
        ts_map1, ts_map2 = await self.banuntil2_get2(mapadvantage_ctf, mapadvantage_ts, channel, "TS")
        ctf_map1, ctf_map2 = await self.banuntil2_get2(mapadvantage_ctf, mapadvantage_ts, channel, "CTF")

        # Add maps to DB
        self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], ts_map1['id']))
        self.bot.conn.commit()
        self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], ts_map2['id']))
        self.bot.conn.commit()
        self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], ctf_map1['id']))
        self.bot.conn.commit()
        self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], ctf_map2['id']))
        self.bot.conn.commit()

        # Set fixture to on-going
        self.bot.cursor.execute("UPDATE Fixtures set status = 2 WHERE id=%s", (fixture_info['id'],))
        self.bot.conn.commit()

        # Remove busy status
        self.bot.fixtures_busy.remove(channel.id)

        # Notify
        await channel.send(self.bot.quotes['cmdPickBan_bo5_end'].format(teamname=team1['name'], tsmap1=ts_map1['name'], tsmap2=ts_map2['name'], ctfmap1=ctf_map1['name'], ctfmap2=ctf_map2['name']))

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
                interaction_ban = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_ts" and i.message.channel.id == channel.id)
                map_toban = maps[int(interaction_ban.component[0].value)]
                user_clicking = discord.utils.get(self.guild.members, id=interaction_ban.author.id)
                if not team_toban_role in user_clicking.roles:
                    await interaction_ban.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=team_toban['name']))
                    continue

                # Ask confirmation
                await interaction_ban.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBan_confirmation'].format(mapname=map_toban['name']), components=[[
                                            Button(style=ButtonStyle.green, label="Yes", custom_id="button_pickban_yes"),
                                            Button(style=ButtonStyle.red, label="No", custom_id="button_pickban_no"),]])
                interaction_banconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction_ban.author.id and i.component.id.startswith("button_pickban_") and i.message.channel.id == channel.id)

                if interaction_banconfirmation.component.id == 'button_pickban_no':
                    continue
                elif interaction_banconfirmation.component.id == 'button_pickban_yes':
                    ban_check = True

            await interaction_banconfirmation.respond(type=6)
            # Ban the map
            maps.remove(map_toban)

            # Edit embed and delete prompt
            await channel.send(self.bot.quotes['cmdPickBan_ban_success'].format(mapname=map_toban['name'], teamname=team_toban['name']))
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
            interaction_pick = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_ts" and i.message.channel.id == channel.id)
            picked_map = maps[int(interaction_pick.component[0].value)]
            user_clicking = discord.utils.get(self.guild.members, id=interaction_pick.author.id)
            if not team_topick_role in user_clicking.roles:
                await interaction_pick.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=mapadvantage_ctf['name']))
                continue

            # Ask confirmation
            await interaction_pick.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBan_pick_confirmation'].format(mapname=picked_map['name']), components=[[
                                        Button(style=ButtonStyle.green, label="Yes", custom_id="button_pickban_yes"),
                                        Button(style=ButtonStyle.red, label="No", custom_id="button_pickban_no"),]])
            interaction_pickconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction_pick.author.id and i.component.id.startswith("button_pickban_") and i.message.channel.id == channel.id)

            if interaction_pickconfirmation.component.id == 'button_pickban_no':
                continue
            elif interaction_pickconfirmation.component.id == 'button_pickban_yes':
                pick_check = True

        await interaction_pickconfirmation.respond(type=6)

        # Delete prompt
        await pickban_prompt_msg.delete()

        await channel.send(self.bot.quotes['cmdPickBan_pick_success'].format(mapname=picked_map['name'], gamemode=gamemode))

        return picked_map  

    async def banuntil2_get2(self, mapadvantage_ctf, mapadvantage_ts, channel, gamemode):
        if gamemode == "TS":
            # Start TS pick and ban
            await channel.send(self.bot.quotes['cmdPickBan_TS_intro'].format(mapadvantage_ctf_role_id=mapadvantage_ctf['role_id'], mapadvantage_ts_role_id=mapadvantage_ts['role_id']))
            # The ts advantage team starts to ban
            team_toban = mapadvantage_ts
        else:
            # Start CTF pick and ban
            await channel.send(self.bot.quotes['cmdPickBan_CTF_intro'].format(mapadvantage_ctf_role_id=mapadvantage_ctf['role_id'], mapadvantage_ts_role_id=mapadvantage_ts['role_id']))
            # The ctf advantage team starts to ban
            team_toban = mapadvantage_ctf

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
                interaction_ban = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_ts" and i.message.channel.id == channel.id)
                map_toban = maps[int(interaction_ban.component[0].value)]
                user_clicking = discord.utils.get(self.guild.members, id=interaction_ban.author.id)
                if not team_toban_role in user_clicking.roles:
                    await interaction_ban.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=team_toban['name']))
                    continue

                # Ask confirmation
                await interaction_ban.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBan_confirmation'].format(mapname=map_toban['name']), components=[[
                                            Button(style=ButtonStyle.green, label="Yes", custom_id="button_pickban_yes"),
                                            Button(style=ButtonStyle.red, label="No", custom_id="button_pickban_no"),]])
                interaction_banconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction_ban.author.id and i.component.id.startswith("button_pickban_") and i.message.channel.id == channel.id)

                if interaction_banconfirmation.component.id == 'button_pickban_no':
                    continue
                elif interaction_banconfirmation.component.id == 'button_pickban_yes':
                    ban_check = True

            await interaction_banconfirmation.respond(type=6)
            # Ban the map
            maps.remove(map_toban)

            # Edit embed and delete prompt
            await channel.send(self.bot.quotes['cmdPickBan_ban_success'].format(mapname=map_toban['name'], teamname=team_toban['name']))
            map_embed = embeds.map_list(maps, embed_title)
            await channel.send(embed=map_embed)
            await pickban_prompt_msg.delete()

            # Switch banning team
            if team_toban == mapadvantage_ctf:
                team_toban = mapadvantage_ts
            else:
                team_toban = mapadvantage_ctf

        return maps[0], maps[1]

    async def pickban_draw(self, fixture_info, team1, team2, channel):

        # Get map lists
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s", ('TS',))
        ts_map_list = self.bot.cursor.fetchall()
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s", ('CTF',))
        ctf_map_list = self.bot.cursor.fetchall()

        # Remove played maps
        self.bot.cursor.execute("SELECT * FROM FixtureMap WHERE fixture_id=%s", (fixture_info['id'],))
        maps_played = self.bot.cursor.fetchall()
        for map_played in maps_played:
            self.bot.cursor.execute("SELECT * FROM Maps WHERE id=%s", (map_played['map_id'],))
            map = self.bot.cursor.fetchone()
            if map in ts_map_list:
                ts_map_list.remove(map)
            elif map in ctf_map_list:
                ctf_map_list.remove(map)

        # Get team roles
        team1_role = discord.utils.get(self.guild.roles, id= int(team1['role_id']))
        team2_role = discord.utils.get(self.guild.roles, id= int(team2['role_id']))


        # Ask winning team what map advantage they want 
        mapadvantage_msg = await channel.send(self.bot.quotes['cmdPickBanDraw_gamemode_advantage_prompt'].format(team1_role_id=team1_role.id), components=[[
            Button(style=ButtonStyle.blue, label="Gamemode", custom_id="button_draw_advantage_gamemode"),
            Button(style=ButtonStyle.blue, label="Map", custom_id="button_draw_advantage_map")
        ]])

        gamemode_advantage_check = False
        while not gamemode_advantage_check:
            interaction_gamemodeadvantage = await self.bot.wait_for("button_click", check = lambda i: i.component.id.startswith("button_draw_advantage_"))
            user_clicking = discord.utils.get(self.guild.members, id=interaction_gamemodeadvantage.author.id)
            if team1_role in user_clicking.roles:
                gamemode_advantage_check = True
            else:
                await interaction_gamemodeadvantage.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=team1['name']))

        if interaction_gamemodeadvantage.component.id == 'button_draw_advantage_gamemode':
            await mapadvantage_msg.edit(self.bot.quotes['cmdPickBanDraw_gamemode_advantage_prompt'].format(team1_role_id=team1_role.id), components=[[
                Button(style=ButtonStyle.green, label="Gamemode", custom_id="button_draw_advantage_gamemode", disabled=True),
                Button(style=ButtonStyle.blue, label="Map", custom_id="button_draw_advantage_map", disabled=True)
            ]])
            gamemode_advantage = team1
            gamemode_advantage_role = team1_role
            map_advantage = team2
            map_advantage_role = team2_role

        
        if interaction_gamemodeadvantage.component.id == 'button_draw_advantage_map':
            await mapadvantage_msg.edit(self.bot.quotes['cmdPickBanDraw_gamemode_advantage_prompt'].format(team1_role_id=team1_role.id), components=[[
                Button(style=ButtonStyle.blue, label="Gamemode", custom_id="button_draw_advantage_gamemode", disabled=True),
                Button(style=ButtonStyle.green, label="Map", custom_id="button_draw_advantage_map", disabled=True)
            ]])
            gamemode_advantage = team2
            gamemode_advantage_role = team2_role
            map_advantage = team1
            map_advantage_role = team1_role

        await interaction_gamemodeadvantage.respond(type=6)
        
        # Get gamemode
        gamemode_msg = await channel.send(self.bot.quotes['cmdPickBanDraw_gamemode_prompt'].format(gamemode_role=gamemode_advantage_role.id), components=[[
            Button(style=ButtonStyle.blue, label="TS", custom_id="button_gamemode_ts"),
            Button(style=ButtonStyle.blue, label="CTF", custom_id="button_gamemode_ctf")
        ]])

        gamemode_check = False
        while not gamemode_check:
            interaction_gamemode = await self.bot.wait_for("button_click", check = lambda i: i.component.id.startswith("button_gamemode_"))
            user_clicking = discord.utils.get(self.guild.members, id=interaction_gamemode.author.id)
            if gamemode_advantage_role in user_clicking.roles:
                gamemode_check = True
            else:
                await interaction_gamemode.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=team1['name']))

        if interaction_gamemode.component.id == 'button_gamemode_ts':
            await gamemode_msg.edit(self.bot.quotes['cmdPickBanDraw_gamemode_prompt'].format(gamemode_role=gamemode_advantage_role.id), components=[[
                Button(style=ButtonStyle.green, label="TS", custom_id="button_gamemode_ts", disabled=True),
                Button(style=ButtonStyle.blue, label="CTF", custom_id="button_gamemode_ctf", disabled=True)
            ]])
            maps = ts_map_list
            gamemode = "TS"

        
        if interaction_gamemode.component.id == 'button_gamemode_ctf':
            await gamemode_msg.edit(self.bot.quotes['cmdPickBanDraw_gamemode_prompt'].format(gamemode_role=gamemode_advantage_role.id), components=[[
                Button(style=ButtonStyle.blue, label="TS", custom_id="button_gamemode_ts", disabled=True),
                Button(style=ButtonStyle.green, label="CTF", custom_id="button_gamemode_ctf", disabled=True)
            ]])
            maps = ctf_map_list
            gamemode = "CTF"

        await interaction_gamemode.respond(type=6)

        # Ban 2 maps
        maps.sort(key=lambda x: x['name'])

        embed_title = f"{gamemode} Maps"

        # Send embeds with the remaining maps
        map_embed = embeds.map_list(maps, embed_title)
        await channel.send(embed=map_embed)

        nb_map_to_remove = 2
        if fixture_info['format'] == 'BO5':
            nb_map_to_remove = 1

        for i in range(nb_map_to_remove):
            # Prompt the ban
            pickban_dropmenu = dropmenus.maps(maps, "pickban_draw")
            pickban_prompt_msg = await channel.send(self.bot.quotes['cmdPickBan_prompt_ban'].format(team_role_id=gamemode_advantage_role.id), components=pickban_dropmenu)

            ban_check = False
            while not ban_check:
                interaction_ban = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_draw" and i.message.channel.id == channel.id)
                map_toban = maps[int(interaction_ban.component[0].value)]
                user_clicking = discord.utils.get(self.guild.members, id=interaction_ban.author.id)
                if not gamemode_advantage_role in user_clicking.roles:
                    await interaction_ban.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=gamemode_advantage['name']))
                    continue

                # Ask confirmation
                await interaction_ban.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBan_confirmation'].format(mapname=map_toban['name']), components=[[
                                            Button(style=ButtonStyle.green, label="Yes", custom_id="button_pickban_yes"),
                                            Button(style=ButtonStyle.red, label="No", custom_id="button_pickban_no"),]])
                interaction_banconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction_ban.author.id and i.component.id.startswith("button_pickban_") and i.message.channel.id == channel.id)

                if interaction_banconfirmation.component.id == 'button_pickban_no':
                    continue
                elif interaction_banconfirmation.component.id == 'button_pickban_yes':
                    ban_check = True

            await interaction_banconfirmation.respond(type=6)
            # Ban the map
            maps.remove(map_toban)

            # Edit embed and delete prompt
            await channel.send(self.bot.quotes['cmdPickBan_ban_success'].format(mapname=map_toban['name'], teamname=gamemode_advantage['name']))
            map_embed = embeds.map_list(maps, embed_title)
            await channel.send(embed=map_embed)
            await pickban_prompt_msg.delete()

        # Pick the map
        pickban_dropmenu = dropmenus.maps(maps, "pickban_ts")
        pickban_prompt_msg = await channel.send(self.bot.quotes['cmdPickBan_prompt_pick'].format(team_role_id=map_advantage_role.id), components=pickban_dropmenu)

        pick_check = False
        while not pick_check:
            interaction_pick = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_ts" and i.message.channel.id == channel.id)
            picked_map = maps[int(interaction_pick.component[0].value)]
            user_clicking = discord.utils.get(self.guild.members, id=interaction_pick.author.id)
            if not map_advantage_role in user_clicking.roles:
                await interaction_pick.respond(content=self.bot.quotes['cmdPickBan_error_wrong_team_click'].format(teamname=map_advantage['name']))
                continue

            # Ask confirmation
            await interaction_pick.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBan_pick_confirmation'].format(mapname=picked_map['name']), components=[[
                                        Button(style=ButtonStyle.green, label="Yes", custom_id="button_pickban_yes"),
                                        Button(style=ButtonStyle.red, label="No", custom_id="button_pickban_no"),]])
            interaction_pickconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction_pick.author.id and i.component.id.startswith("button_pickban_") and i.message.channel.id == channel.id)

            if interaction_pickconfirmation.component.id == 'button_pickban_no':
                continue
            elif interaction_pickconfirmation.component.id == 'button_pickban_yes':
                pick_check = True

        await interaction_pickconfirmation.respond(type=6)

        # Delete prompt
        await pickban_prompt_msg.delete()

        await channel.send(self.bot.quotes['cmdPickBan_pick_success'].format(mapname=picked_map['name'], gamemode=gamemode))


        # Add map to DB
        self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], picked_map['id']))
        self.bot.conn.commit()

        # Remove busy status
        self.bot.fixtures_busy.remove(channel.id)

        # Notify
        await channel.send(self.bot.quotes['cmdPickBan_draw_end'].format(teamname=team1['name'], gamemode=gamemode, map=picked_map['name']))

        # Update fixtures
        self.bot.async_loop.create_task(update.fixtures(self.bot))  

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

        if not roster_info:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"Error, you are not in one of the two teams concerned by this game.")
            self.bot.users_busy.remove(interaction.author.id)
            return

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

        gameschedule = str(datetime.datetime.combine(gamedate_formatted, gametime_formatted))


        await interaction.message.channel.send(self.bot.quotes['cmdSchedule_invitation'].format(roleid=other_team_info['role_id'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime), components=
            [[
            Button(style=5, label="Convert to your timezone", url=utils.timezone_link(gameschedule), custom_id="button_schedule_timezone_link")],
            [
            Button(style=ButtonStyle.green, label="Accept", custom_id=f"button_accept_fixture_schedule_{other_team_info['id']}_{gameschedule}"),
            Button(style=ButtonStyle.red, label="Decline", custom_id=f"button_decline_fixture_schedule_{other_team_info['id']}_{gameschedule}")
            ]])

        # Update last proposal date
        self.bot.cursor.execute("UPDATE Fixtures SET date_last_proposal=%s WHERE id=%s", (datetime.datetime.now(), fixture_info['id']))
        self.bot.conn.commit()

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSchedule_invitation_log'].format(otherteamname=other_team_info['name'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime))


    async def schedule_fixture_admin(self, interaction):
        # Check if user is busy
        if interaction.author.id in self.bot.users_busy:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdErrorBusy'])
            return
                
        # Get fixture info
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Get clans info
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
        team_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
        other_team_info = self.bot.cursor.fetchone()

        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"Check dms!")

        # Flag as busy
        self.bot.users_busy.append(interaction.author.id)

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
        await interaction.message.channel.send(self.bot.quotes['cmdSchedule_accepted_admin'].format(otherroleid=other_team_info['role_id'], roleid=team_info['role_id'], gamedate=gamedate, gametime=gametime), components=[[
            Button(style=5, label="Convert to your timezone", url=utils.timezone_link(gamedate_str), custom_id="button_schedule_timezone_link")
        ]])

        # Update embed
        embed_message = await interaction.channel.fetch_message(fixture_info['embed_id'])
        fixture_embed, components = await embeds.fixture(self.bot, fixture_id=fixture_info['id'])
        await embed_message.edit(embed=fixture_embed, components=components)

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSchedule_accepted_admin_log'].format(otherteamname=other_team_info['name'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime))

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
        gameschedule = str(datetime.datetime.combine(gamedate, gametime))
        
        # Check if the other team clicked
        invited_team_id = interaction.component.id.split("_")[-2]
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
        await interaction.message.channel.send(self.bot.quotes['cmdSchedule_accepted_success'].format(teamname=team_info['name'],otherroleid=other_team_info['role_id'], roleid=team_info['role_id'], gamedate=gamedate, gametime=gametime), components=[[
            Button(style=5, label="Convert to your timezone", url=utils.timezone_link(gameschedule), custom_id="button_schedule_timezone_link")
        ]])

        await interaction.message.delete()

        # Update embed
        embed_message = await interaction.channel.fetch_message(fixture_info['embed_id'])
        fixture_embed, components = await embeds.fixture(self.bot, fixture_id=fixture_info['id'])
        await embed_message.edit(embed=fixture_embed, components=components)

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSchedule_accepted_log'].format(otherteamname=other_team_info['name'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime, username=user_info['ingame_name']))

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
        if int(team_info['id']) != int(invited_team_id):
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSchedule_error_notinteam'].format(otherteamname=other_team_info['name']))
            return
        
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSchedule_declined'])

        # Notify
        await interaction.message.channel.send(self.bot.quotes['cmdSchedule_declined_success'].format(otherroleid=other_team_info['role_id'], gamedate=gamedate, gametime=gametime))

        await interaction.message.delete()


        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSchedule_declined_log'].format(otherteamname=other_team_info['name'], teamname=team_info['name'], gamedate=gamedate, gametime=gametime, username=user_info['ingame_name']))

    async def enter_scores(self, interaction):
        # Get fixture info
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Get clans info
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team1'],))
        team1_info = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Teams WHERE id=%s", (fixture_info['team2'],))
        team2_info = self.bot.cursor.fetchone()

        # Check if match has been setup
        if not fixture_info['status'] or int(fixture_info['status']) == 1:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEnterScores_error_notsetup'])
            return

        # Check if user is busy
        if interaction.author.id in self.bot.users_busy:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdErrorBusy'])
            return

        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['CheckDm'])

        # Get all maps played
        self.bot.cursor.execute("SELECT * FROM FixtureMap WHERE fixture_id=%s", (fixture_info['id'],))
        maps_played = self.bot.cursor.fetchall()

        # Flag user as busy
        self.bot.users_busy.append(interaction.author.id)

        winning_teams = []
        for map_played in maps_played:
            # Get the map and mode
            self.bot.cursor.execute("SELECT * FROM Maps WHERE id=%s", (map_played['map_id'],))
            map_info = self.bot.cursor.fetchone()


            # Get team 1 score
            score_check = False
            while not score_check:
                await interaction.author.send(self.bot.quotes['cmdEnterScores_prompt_scores'].format(teamname=team1_info['name'], mapname=map_info['name'], gamemode=map_info['gamemode']))

                def check(m):
                    return m.author == interaction.author and m.guild == None

                team1_score_msg = await self.bot.wait_for('message', check=check)
                team1_score = team1_score_msg.content.lower().strip()

                # Cancel 
                if team1_score.lower() == '!cancel':
                    await interaction.author.send(self.bot.quotes['cmdEnterScores_cancel'])
                    # Remove busy status
                    self.bot.users_busy.remove(interaction.author.id)
                    return

                if not team1_score.isnumeric():
                    await interaction.author.send(self.bot.quotes['cmdCreateCup_error_nbofteams'])
                    continue

                score_check = True

            # Do again for team2
            score_check = False
            while not score_check:
                await interaction.author.send(self.bot.quotes['cmdEnterScores_prompt_scores'].format(teamname=team2_info['name'], mapname=map_info['name'], gamemode=map_info['gamemode']))

                def check(m):
                    return m.author == interaction.author and m.guild == None

                team2_score_msg = await self.bot.wait_for('message', check=check)
                team2_score = team2_score_msg.content.lower().strip()

                # Cancel 
                if team2_score.lower() == '!cancel':
                    await interaction.author.send(self.bot.quotes['cmdEnterScores_cancel'])
                    # Remove busy status
                    self.bot.users_busy.remove(interaction.author.id)
                    return

                if not team2_score.isnumeric():
                    await interaction.author.send(self.bot.quotes['cmdCreateCup_error_nbofteams'])
                    continue

                # Check if scores are equal (impossible with OT)
                if team1_score == team2_score:
                    await interaction.author.send(self.bot.quotes['cmdEnterScores_error_equal'])
                    continue

                score_check = True

            team1_score = int(team1_score)
            team2_score = int(team2_score)

            if team1_score > team2_score:
                winning_teams.append(team1_info)
            else:
                winning_teams.append(team2_info)


            # Update score in DB
            self.bot.cursor.execute("UPDATE FixtureMap set team1_score = %s, team2_score = %s WHERE id=%s", (team1_score, team2_score, map_played['id']))
            self.bot.conn.commit()

        # Remove busy status
        self.bot.users_busy.remove(interaction.author.id)


        # Check which team won the game
        team1_wins = 0
        team1_draws = 0
        team1_loss = 0
        team2_wins = 0
        team2_draws = 0
        team2_loss = 0

        if winning_teams.count(team1_info) > winning_teams.count(team2_info):
            team1_points = 3
            team1_wins = 1
            team2_points = 0
            team2_loss = 1

        elif winning_teams.count(team2_info) > winning_teams.count(team1_info):
            team2_points = 3
            team2_wins = 1
            team1_points = 0
            team1_loss = 1
        else:
            team1_points = 1
            team1_draws = 1
            team2_points = 1
            team2_draws = 1

        # Get signup info
        self.bot.cursor.execute("SELECT * FROM Signups WHERE cup_id=%s and team_id=%s", (fixture_info['cup_id'], fixture_info['team1']))
        signup_team1 = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM Signups WHERE cup_id=%s and team_id=%s", (fixture_info['cup_id'], fixture_info['team2']))
        signup_team2 = self.bot.cursor.fetchone()

        # Ask if we want to add points on the divisions ranking might say no if this is playoffs
        await interaction.author.send(self.bot.quotes["cmdEnterScores_prompt_points"].format(team1_name=team1_info['name'], team1_points=team1_points, team2_name=team2_info['name'], team2_points=team2_points, divnumber=signup_team1['div_number']), components=[[
            Button(style=ButtonStyle.green, label="Yes", custom_id="button_enterscores_addpoints_yes"),
            Button(style=ButtonStyle.red, label="No", custom_id="button_enterscores_addpoints_no")
        ]])

        interaction_addpointsconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction.author.id and i.component.id.startswith("button_enterscores_addpoints_"))

        if interaction_addpointsconfirmation.component.id == 'button_enterscores_addpoints_no':
            await interaction_addpointsconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEnterScores_addpoints_no'])
            
        elif interaction_addpointsconfirmation.component.id == 'button_enterscores_addpoints_yes':
            # Add the points 
            if signup_team1['points']:
                team1_points = int(signup_team1['points']) + team1_points
            if signup_team1['win']:
                team1_wins = int(signup_team1['win']) + team1_wins
            if signup_team1['draw']:
                team1_draws = int(signup_team1['draw']) + team1_draws
            if signup_team1['loss']:
                team1_loss = int(signup_team1['loss']) + team1_loss
            if signup_team2['points']:
                team2_points = int(signup_team2['points']) + team2_points
            if signup_team2['win']:
                team2_wins = int(signup_team2['win']) + team2_wins
            if signup_team2['draw']:
                team2_draws = int(signup_team2['draw']) + team2_draws
            if signup_team2['loss']:
                team2_loss = int(signup_team2['loss']) + team2_loss

            # Edit DB
            self.bot.cursor.execute("UPDATE Signups SET points = %s, win = %s, draw = %s, loss = %s WHERE cup_id=%s and team_id=%s", (team1_points, team1_wins, team1_draws, team1_loss, fixture_info['cup_id'], team1_info['id']))
            self.bot.conn.commit()
            self.bot.cursor.execute("UPDATE Signups SET points = %s, win = %s, draw = %s, loss = %s WHERE cup_id=%s and team_id=%s", (team2_points, team2_wins, team2_draws, team2_loss, fixture_info['cup_id'], team2_info['id']))
            self.bot.conn.commit()

            await interaction_addpointsconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEnterScores_addpoints_yes'])

            self.bot.async_loop.create_task(update.signups(self.bot))

        # Get players of both teams
        self.bot.cursor.execute("SELECT * FROM Roster s INNER JOIN Users u ON s.player_id = u.id WHERE (s.accepted = 1 or s.accepted = 2) and s.team_id=%s", (team1_info['id'],))
        players_team1 = self.bot.cursor.fetchall()
        self.bot.cursor.execute("SELECT * FROM Roster s INNER JOIN Users u ON s.player_id = u.id WHERE (s.accepted = 1 or s.accepted = 2) and s.team_id=%s", (team2_info['id'],))
        players_team2 = self.bot.cursor.fetchall()

        # Prepare buttons
        players_buttons_team1 = dropmenus.player_played(players_team1)
        players_buttons_team2 = dropmenus.player_played(players_team2)

        # Ask for team1
        player_played_team1_msg = await interaction.author.send(self.bot.quotes['cmdEnterScores_prompt_players'].format(teamname=team1_info['name']), components=players_buttons_team1)
        players_checked = False
        team1_players_played = []

        # Wait for all the players to be selected
        while not players_checked:
            interaction_playerplayed = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction.author.id and i.component.id.startswith("button_player_played_"))
            player_id = interaction_playerplayed.component.id.split("_")[-1]

            if player_id == "validate":
                players_checked = True
                await interaction_playerplayed.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEnterScores_players_success'])

            else:
                if int(player_id) in team1_players_played:
                    team1_players_played.remove(int(player_id))
                else:
                    team1_players_played.append(int(player_id))

                players_buttons_team1 = dropmenus.player_played(players_team1, team1_players_played)
                await player_played_team1_msg.edit(self.bot.quotes['cmdEnterScores_prompt_players'].format(teamname=team1_info['name']), components=players_buttons_team1)

                await interaction_playerplayed.respond(type=6)

        # Ask for team2
        player_played_team2_msg = await interaction.author.send(self.bot.quotes['cmdEnterScores_prompt_players'].format(teamname=team2_info['name']), components=players_buttons_team2)
        players_checked = False
        team2_players_played = []

        # Wait for all the players to be selected
        while not players_checked:
            interaction_playerplayed = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction.author.id and i.component.id.startswith("button_player_played_"))
            player_id = interaction_playerplayed.component.id.split("_")[-1]

            if player_id == "validate":
                players_checked = True
                await interaction_playerplayed.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEnterScores_players_success'])

            else:
                if int(player_id) in team2_players_played:
                    team2_players_played.remove(int(player_id))
                else:
                    team2_players_played.append(int(player_id))

                players_buttons_team2 = dropmenus.player_played(players_team2, team2_players_played)
                await player_played_team2_msg.edit(self.bot.quotes['cmdEnterScores_prompt_players'].format(teamname=team2_info['name']), components=players_buttons_team2)

                await interaction_playerplayed.respond(type=6)

        # Delete existing
        self.bot.cursor.execute("DELETE FROM FixturePlayer WHERE fixture_id = %s", (fixture_info['id'],))
        self.bot.conn.commit()

        # Insert into DB
        for player_id in team1_players_played:
            self.bot.cursor.execute("INSERT INTO FixturePlayer (fixture_id, player_id) VALUES (%s, %s)", (fixture_info['id'], player_id))
            self.bot.conn.commit()
        for player_id in team2_players_played:
            self.bot.cursor.execute("INSERT INTO FixturePlayer (fixture_id, player_id) VALUES (%s, %s)", (fixture_info['id'], player_id))
            self.bot.conn.commit()

        # Get cup info and post results
        self.bot.cursor.execute("SELECT * FROM Cups WHERE id=%s", (fixture_info['cup_id'],))
        cup_info = self.bot.cursor.fetchone()

        if interaction.message.channel.name.startswith("round"):
            match_type = interaction.message.channel.category.name.split('┋')[2].split()[0]
        else:
            match_type = interaction.message.channel.name.split('┋')[0].title().replace('-', " ")
        results_chan = discord.utils.get(self.guild.channels, id=int(cup_info['chan_results_id']))
        if results_chan:
            result_str = embeds.results(self.bot, fixture_info, match_type)
            await results_chan.send(result_str)

        # Set fixture to compeleted
        if int(fixture_info['status']) == 2:
            self.bot.cursor.execute("UPDATE Fixtures set status = 3 WHERE id=%s", (fixture_info['id'],))
            self.bot.conn.commit()

        # Refresh all fixture status
        serverLoopCog = self.bot.get_cog('ServerLoop')
        await serverLoopCog.check_upload_status()
        await serverLoopCog.refresh_all_fixture_status()

        # Update embed
        embed_message = await interaction.channel.fetch_message(fixture_info['embed_id'])
        fixture_embed, components = await embeds.fixture(self.bot, fixture_id=fixture_info['id'])
        await embed_message.edit(embed=fixture_embed, components=components)

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEnterScores_success'].format(team1name=team1_info['name'], team2name=team2_info['name']))

    async def change_map_fixture_admin(self, interaction):
        # Get fixture info
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        # Get old maps info
        self.bot.cursor.execute("SELECT * FROM FixtureMap f INNER JOIN Maps m ON f.map_id = m.id WHERE f.fixture_id = %s and gamemode='TS'", (fixture_info['id'],))
        old_map_ts = self.bot.cursor.fetchone()
        self.bot.cursor.execute("SELECT * FROM FixtureMap f INNER JOIN Maps m ON f.map_id = m.id WHERE f.fixture_id = %s and gamemode='CTF'", (fixture_info['id'],))
        old_map_ctf = self.bot.cursor.fetchone()

        

        # TODO: Implement BO3 and BO5
        # Get the TS map
        # Get maps
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s;", ("TS",))
        maps_ts = self.bot.cursor.fetchall()
        self.bot.cursor.execute("SELECT * FROM Maps WHERE gamemode=%s;", ("CTF",))
        maps_ctf = self.bot.cursor.fetchall()
        maps_ts.sort(key=lambda x: x['name'])
        maps_ctf.sort(key=lambda x: x['name'])

        pickban_dropmenu_ts = dropmenus.maps(maps_ts, "pickban_ts")
        pickban_dropmenu_ctf = dropmenus.maps(maps_ctf, "pickban_ctf")

        #Prompt for TS
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdChangeMap_prompt_map'].format(gamemode="TS"), components=pickban_dropmenu_ts)
        interaction_map_ts = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_ts")
        map_ts = maps_ts[int(interaction_map_ts.component[0].value)]

        #Prompt for CTF
        await interaction_map_ts.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdChangeMap_prompt_map'].format(gamemode="CTF"), components=pickban_dropmenu_ctf)
        interaction_map_ctf = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "pickban_ctf")
        map_ctf = maps_ctf[int(interaction_map_ctf.component[0].value)]

        # Check if pick and ban has been done
        if not fixture_info['status'] or int(fixture_info['status']) == 1:
            # Add maps to DB
            self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], map_ts['id']))
            self.bot.conn.commit()
            self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], map_ctf['id']))
            self.bot.conn.commit()

            # Set fixture to on-going
            self.bot.cursor.execute("UPDATE Fixtures set status = 2 WHERE id=%s", (fixture_info['id'],))
            self.bot.conn.commit()
        else:
            # Update in DB
            self.bot.cursor.execute("DELETE FROM FixtureMap  WHERE fixture_id = %s", (fixture_info['id'],))
            self.bot.conn.commit()
            
            # Add maps to DB
            self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], map_ts['id']))
            self.bot.conn.commit()
            self.bot.cursor.execute("INSERT INTO FixtureMap (fixture_id, map_id) VALUES (%s, %s)", (fixture_info['id'], map_ctf['id']))
            self.bot.conn.commit()

        await interaction_map_ctf.respond(type=InteractionType.ChannelMessageWithSource, content="Success!")

        # Update embed
        embed_message = await interaction.channel.fetch_message(fixture_info['embed_id'])
        fixture_embed, components = await embeds.fixture(self.bot, fixture_id=fixture_info['id'])
        await embed_message.edit(embed=fixture_embed, components=components)






        

def setup(bot):
    bot.add_cog(Fixtures(bot))
