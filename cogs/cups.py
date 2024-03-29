import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check
import cogs.common.dropmenus as dropmenus

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component

from ftwgl import FTWClient


class Cups(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        user = discord.utils.get(self.guild.members, id=interaction.user.id)
        # Get user info
        user_info = self.bot.db.get_player(discord_id=user.id)

        # Get the cup to edit
        cup_id = interaction.component.id.split("_")[-1]
        is_admin = interaction.component.id.split("_")[-2] == "admin"

        # Get cup info
        cup_info = self.bot.db.get_cup(chan_admin_id=interaction.message.channel.id)
        if not cup_info:
            cup_info = self.bot.db.get_cup(id=cup_id)

        if interaction.component.id.startswith("button_signup_"):
            await self.signup(cup_info, user, user_info, is_admin, interaction)
        elif interaction.component.id.startswith("button_edit_cup_name"):
            await self.change_cup_name(cup_info, user, user_info, is_admin, interaction)
        elif interaction.component.id.startswith("button_edit_cup_mini_roster"):
            await self.change_cup_roster_req(cup_info, user, user_info, is_admin, interaction)
        elif interaction.component.id.startswith("button_edit_signupdates"):
            await self.change_cup_signup_dates(cup_info, user, user_info, is_admin, interaction)
        elif interaction.component.id.startswith("button_create_division"):
            await self.create_division(cup_info, user, user_info, is_admin, interaction)
        elif interaction.component.id.startswith("button_add_team_div"):
            await self.add_team_division(cup_info, user, user_info, is_admin, interaction)
        elif interaction.component.id.startswith("button_remove_team_div"):
            await self.remove_team_division(cup_info, user, user_info, is_admin, interaction)
        elif interaction.component.id.startswith("button_fixpoints_"):
            await self.fix_points_division(cup_info, user, user_info, is_admin, interaction)
        elif interaction.component.id.startswith("button_delete_div"):
            await self.delete_division(cup_info, user, user_info, is_admin, interaction)
        else:
            return

        # Update signup 
        self.bot.async_loop.create_task(update.signups(self.bot))



    @commands.command() 
    @check.is_guild_manager()
    async def createcup(self, ctx):
        # Flag the user as busy
        self.bot.users_busy.append(ctx.author.id)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        # Wait for cup name
        await ctx.send(self.bot.quotes['cmdCreateCup_prompt_name'])
        name_msg = await self.bot.wait_for('message', check=check)
        name = name_msg.content.strip()

        # Cancel 
        if name.lower() == '!cancel':
            await ctx.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
            # Remove busy status
            self.bot.users_busy.remove(ctx.author.id)
            return
        
        '''
        # Wait for number of teams and check validity
        number_of_teams_checked = False
        while not number_of_teams_checked:
            await ctx.send(self.bot.quotes['cmdCreateCup_prompt_nbofteams'])
            number_of_teams_msg = await self.bot.wait_for('message', check=check)
            number_of_teams = number_of_teams_msg.content.lower().strip()

            if not number_of_teams.isnumeric():
                await ctx.send(self.bot.quotes['cmdCreateCup_error_nbofteams'])

            # Cancel 
            if number_of_teams.lower() == '!cancel':
                await ctx.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(ctx.author.id)
                return

            else:
                number_of_teams = int(number_of_teams)
                number_of_teams_checked = True
        '''

        # Wait for minimum number of players per roster and check validity
        number_of_miniroster_checked = False
        while not number_of_miniroster_checked:
            await ctx.send(self.bot.quotes['cmdCreateCup_prompt_miniroster'])
            number_of_miniroster_msg = await self.bot.wait_for('message', check=check)
            mini_roster = number_of_miniroster_msg.content.lower().strip()

            # Cancel 
            if mini_roster.lower() == '!cancel':
                await ctx.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(ctx.author.id)
                return

            if not mini_roster.isnumeric():
                await ctx.send(self.bot.quotes['cmdCreateCup_error_nbofteams'])

            else:
                mini_roster = int(mini_roster)
                number_of_miniroster_checked = True

        # Wait for maximum number of players per roster and check validity
        number_of_maxiroster_checked = False
        while not number_of_maxiroster_checked:
            await ctx.send(self.bot.quotes['cmdCreateCup_prompt_maxiroster'])
            number_of_maxiroster_msg = await self.bot.wait_for('message', check=check)
            maxi_roster = number_of_maxiroster_msg.content.lower().strip()

            # Cancel 
            if maxi_roster.lower() == '!cancel':
                await ctx.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(ctx.author.id)
                return

            if not maxi_roster.isnumeric():
                await ctx.send(self.bot.quotes['cmdCreateCup_error_nbofteams'])

            elif int(maxi_roster) < int(mini_roster):
                await ctx.send(self.bot.quotes['cmdCreateCup_error_maxiroster'])

            else:
                maxi_roster = int(maxi_roster)
                number_of_maxiroster_checked = True

        # Wait for signup start date and check validity
        signup_start_date_checked = False
        while not signup_start_date_checked:
            await ctx.send(self.bot.quotes['cmdCreateCup_prompt_signupstart'])
            signupstart_msg = await self.bot.wait_for('message', check=check)
            signupstart = signupstart_msg.content.lower().strip()

            # Cancel 
            if signupstart == '!cancel':
                await ctx.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(ctx.author.id)
                return

            signup_start_date_checked, signup_start_date = utils.check_date_format(signupstart)

            if not signup_start_date_checked:
                await ctx.send(self.bot.quotes['cmdCreateCup_error_date'])


        # Wait for signup end date and check validity
        signup_end_date_checked = False
        while not signup_end_date_checked:
            await ctx.send(self.bot.quotes['cmdCreateCup_prompt_signupend'])
            signupend_msg = await self.bot.wait_for('message', check=check)
            signupend = signupend_msg.content.lower().strip()

            # Cancel 
            if signupend == '!cancel':
                await ctx.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(ctx.author.id)
                return

            signup_end_date_checked, signup_end_date = utils.check_date_format(signupend)

            if not signup_end_date_checked:
                await ctx.send(self.bot.quotes['cmdCreateCup_error_date'])
                continue

            # Check if the end date is after the start date
            if signup_start_date > signup_end_date:
                await ctx.send(self.bot.quotes['cmdCreateCup_error_startdate'])
                signup_end_date_checked = False
                continue

        # Remove busy status
        self.bot.users_busy.remove(ctx.author.id)

        # Create category and channels
        role_flawless = discord.utils.get(self.guild.roles, id=int(self.bot.role_flawless_crew_id))
        role_streamer = discord.utils.get(self.guild.roles, id=int(self.bot.role_streamer_id))
        role_bot = discord.utils.get(self.guild.roles, id=int(self.bot.role_bot_id))
        role_unreg = discord.utils.get(self.guild.roles, id=int(self.bot.role_unregistered_id))
        category = await self.guild.create_category_channel(f"\U0001F947┋ {name}")
        await category.set_permissions(self.guild.default_role, send_messages=False)
        await category.set_permissions(role_flawless, send_messages=True)
        await category.set_permissions(role_bot, send_messages=True)
        await category.set_permissions(role_unreg, view_channel=False)

        # get admin channel permissions and send commands
        chan_admin = await category.create_text_channel("admin-panel")
        await chan_admin.set_permissions(role_bot, view_channel=True)
        await chan_admin.set_permissions(self.guild.default_role, view_channel=False)
        await chan_admin.set_permissions(role_flawless, view_channel=True)
        await chan_admin.send("Commands to edit the cup in general", components=[[
                                    Button(style=ButtonStyle.blue, label="Change cup name", custom_id="button_edit_cup_name"),
                                    Button(style=ButtonStyle.blue, label="Change roster req.", custom_id="button_edit_cup_mini_roster"),
                                    Button(style=ButtonStyle.blue, label="Change signup dates", custom_id="button_edit_signupdates")
                                ],
                                [
                                    Button(style=ButtonStyle.green, label="Create division", custom_id="button_create_division"),
                                ]])
        await chan_admin.send("Commands to edit the cup fixtures", components=[[
                                    Button(style=ButtonStyle.green, label="Create a fixture", custom_id="button_create_fixture"),
                                    Button(style=ButtonStyle.blue, label="Schedule a game", custom_id="button_schedule"),
                                    Button(style=ButtonStyle.blue, label="Enter scores", custom_id="button_enter_scores")
                                ],
                                [
                                    Button(style=ButtonStyle.red, label="Delete fixture", custom_id="button_delete_fixture"),
                                ]])
        

        chan_signups = await category.create_text_channel("signups")
        chan_calendar = await category.create_text_channel("calendar")
        chan_stage = await category.create_text_channel("stage")
        chan_results = await category.create_text_channel("results")

        # Create Match schedule and match index chan
        category_match_schedule = await self.guild.create_category_channel(f"{name}┋ \U0001F4C5 Match Schedule")
        chan_match_index = await category.create_text_channel("match-index")
        await chan_match_index.set_permissions(role_bot, view_channel=True)
        await chan_match_index.set_permissions(self.guild.default_role, view_channel=False)
        await chan_match_index.set_permissions(role_flawless, view_channel=True)
        await chan_match_index.set_permissions(role_streamer, view_channel=True)

        ftw_client: FTWClient = self.bot.ftw
        ftw_cup_id = await ftw_client.cup_create(
            name=name,
            abbreviation=utils.create_abbreviation(name),
            playoff_length=None,
            minimum_roster_size=mini_roster,
            start_date=signup_start_date,
            roster_lock_date=signup_end_date)

        cup_id = self.bot.db.create_cup(name, mini_roster, signup_start_date, signup_end_date, category.id, chan_admin.id, chan_signups.id, chan_calendar.id, chan_stage.id, category_match_schedule.id, chan_match_index.id, maxi_roster, chan_results.id, ftw_cup_id)

        # Post index
        #match_index_embed = await embeds.match_index(self.bot, cup_id)
        #await chan_match_index.send(embed=match_index_embed)

        # Print log
        await ctx.channel.send(self.bot.quotes['cmdCreateCup_success'])

        # Update fixtures
        await update.fixtures(self.bot)

    @commands.command() 
    @check.is_guild_manager()
    async def forcesignup(self, ctx, tag):
        # Check if we are in the admin chan of a cup
        cup = self.bot.db.get_cup(chan_admin_id=ctx.channel.id)

        if not cup:
            await ctx.send(self.bot.quotes['cmdForceSignup_error_NoCup'], delete_after=2)
            await ctx.message.delete()
            return

        # Check if the tag is valid
        team = self.bot.db.get_clan(tag=tag)

        if not team:
            await ctx.send(self.bot.quotes['cmdForceSignup_error_NoTeam'], delete_after=2)
            await ctx.message.delete()
            return

        # Check if already signed up
        if self.bot.db.get_clan_signup(team['id'], cup['id']):
            await ctx.send(self.bot.quotes['cmdForceSignup_error_AlreadySignedUp'], delete_after=2)
            await ctx.message.delete()
            return

        # Signup the clan 
        self.bot.db.signup_clan(team['id'], cup['id'])

        ftw_client: FTWClient = self.bot.ftw
        await ftw_client.cup_add_team(team['ftw_team_id'], cup['ftw_cup_id'])

        await ctx.message.delete()
        await ctx.send(self.bot.quotes['cmdForceSignup_success'], delete_after=2)
        
        # Update log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSignup_log'].format(teamname=team['name'], cupname=cup['name']))

        self.bot.async_loop.create_task(update.signups(self.bot))

    @commands.command() 
    @check.is_guild_manager()
    async def forceremovesignup(self, ctx, tag):
        # Check if we are in the admin chan of a cup
        cup = self.bot.db.get_cup(chan_admin_id=ctx.channel.id)

        if not cup:
            await ctx.send(self.bot.quotes['cmdForceSignup_error_NoCup'], delete_after=2)
            await ctx.message.delete()
            return

        # Check if the tag is valid
        team = self.bot.db.get_clan(tag=tag)

        if not team:
            await ctx.send(self.bot.quotes['cmdForceSignup_error_NoTeam'], delete_after=2)
            await ctx.message.delete()
            return

        # Check if already signed up
        if not self.bot.db.get_clan_signup(team['id'], cup['id']):
            await ctx.send(self.bot.quotes['cmdForceRemoveSignup_error_AlreadySignedUp'], delete_after=2)
            await ctx.message.delete()
            return

        # Ask confirmation
        confirmation_msg = await ctx.send(self.bot.quotes['cmdForceRemoveSignup_confirmation'].format(teamname=team['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_removesignup_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_removesignup_no"),]])
        interaction_confirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == ctx.author.id and i.component.id.startswith("button_removesignup_"))

        if interaction_confirmation.component.id == 'button_removesignup_no':
            await ctx.send(self.bot.quotes['cmdForceRemoveSignup_cancel'], delete_after=2)
            await ctx.message.delete()
            await confirmation_msg.delete()
            return
        
        if interaction_confirmation.component.id == 'button_removesignup_yes':
            # Remove clan from signups # TODO : check if remove fixtures too 
            self.bot.db.remove_signup_clan(team['id'], cup['id'])
            await ctx.message.delete()
            await confirmation_msg.delete()
            await ctx.send(self.bot.quotes['cmdForceRemoveSignup_success'], delete_after=2)
            
            # Update log
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdForceRemoveSignup_log'].format(teamname=team['name'], cupname=cup['name']))

            self.bot.async_loop.create_task(update.signups(self.bot))

    async def change_cup_name(self, cup_info, user, user_info, is_admin, interaction):

        # Flag the user as busy
        self.bot.users_busy.append(interaction.author.id)

        await interaction.respond(type=6)

        def check(m):
            return m.author == interaction.author and m.channel == interaction.message.channel

        # Wait for cup name
        prompt_msg = await interaction.message.channel.send(self.bot.quotes['cmdCreateCup_prompt_name'])
        name_msg = await self.bot.wait_for('message', check=check)
        name = name_msg.content.strip()

        # Cancel 
        if name.lower() == '!cancel':
            #await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEditCup_cancel'])
            # Delete msgs
            await prompt_msg.delete()
            await name_msg.delete()
            # Remove busy status
            self.bot.users_busy.remove(interaction.author.id)
            return

        # Update name
        self.bot.db.edit_cup(id=cup_info['id'], name=name)

        # Rename category #TODO: check if need to rename fixtures
        category =  discord.utils.get(self.guild.channels, id=int(cup_info['category_id']))
        await category.edit(name=f"\U0001F947┋ {name}")

        # Delete msgs
        await prompt_msg.delete()
        await name_msg.delete()

        # Log
        #await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEditCupRename_success'])
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEditCupRename_log'].format(oldname=cup_info['name'], newname=name))

        # Remove busy status
        self.bot.users_busy.remove(interaction.author.id)

    async def change_cup_roster_req(self, cup_info, user, user_info, is_admin, interaction):

        # Flag the user as busy
        self.bot.users_busy.append(interaction.author.id)

        await interaction.respond(type=6)

        def check(m):
            return m.author == interaction.author and m.channel == interaction.message.channel

        # Wait for minimum number of players per roster and check validity
        number_of_miniroster_checked = False
        error_msg = None
        while not number_of_miniroster_checked:
            prompt_msg = await interaction.message.channel.send(self.bot.quotes['cmdCreateCup_prompt_miniroster'])
            number_of_miniroster_msg = await self.bot.wait_for('message', check=check)
            mini_roster = number_of_miniroster_msg.content.lower().strip()

            # Delete error message if any
            try:
                await error_msg.delete()
            except:
                pass

            # Cancel 
            if mini_roster.lower() == '!cancel':
                await prompt_msg.delete()
                await number_of_miniroster_msg.delete()
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            if not mini_roster.isnumeric():
                await prompt_msg.delete()
                await number_of_miniroster_msg.delete()
                error_msg = await interaction.message.channel.send(self.bot.quotes['cmdCreateCup_error_nbofteams'])
                continue

            else:
                mini_roster = int(mini_roster)
                number_of_miniroster_checked = True
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)

        # Update mini roster
        self.bot.db.edit_cup(id=cup_info['id'], mini_roster=mini_roster)

        # Delete msgs
        await prompt_msg.delete()
        await number_of_miniroster_msg.delete()

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEditCupMiniRoster_log'].format(cupname=cup_info['name'], oldminiroster=cup_info['mini_roster'], newminiroster=mini_roster))

    async def change_cup_signup_dates(self, cup_info, user, user_info, is_admin, interaction):

        # Flag the user as busy
        self.bot.users_busy.append(interaction.author.id)

        await interaction.respond(type=6)

        def check(m):
            return m.author == interaction.author and m.channel == interaction.message.channel

        # Wait for signup start date and check validity
        signup_start_date_checked = False
        while not signup_start_date_checked:
            signup_start_prompt_msg = await interaction.message.channel.send(self.bot.quotes['cmdCreateCup_prompt_signupstart'])
            signupstart_msg = await self.bot.wait_for('message', check=check)
            signupstart = signupstart_msg.content.lower().strip()

            # Delete error message if any
            try:
                await error_msg.delete()
            except:
                pass

            # Cancel 
            if signupstart == '!cancel':
                # Delete messages
                await signup_start_prompt_msg.delete()
                await signupstart_msg.delete()
                
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            signup_start_date_checked, signup_start_date = utils.check_date_format(signupstart)

            if not signup_start_date_checked:
                await signup_start_prompt_msg.delete()
                await signupstart_msg.delete()
                error_msg = await interaction.message.channel.send(self.bot.quotes['cmdCreateCup_error_date'])


        # Wait for signup end date and check validity
        signup_end_date_checked = False
        while not signup_end_date_checked:
            signup_end_prompt_msg = await interaction.message.channel.send(self.bot.quotes['cmdCreateCup_prompt_signupend'])
            signupend_msg = await self.bot.wait_for('message', check=check)
            signupend = signupend_msg.content.lower().strip()

            # Delete error message if any
            try:
                await error_msg.delete()
            except:
                pass

            # Cancel 
            if signupend == '!cancel':
                # Delete messages
                await signup_start_prompt_msg.delete()
                await signupstart_msg.delete()
                await signup_end_prompt_msg.delete()
                await signupend_msg.delete()
                
                # Remove busy status
                self.bot.users_busy.remove(interaction.author.id)
                return

            signup_end_date_checked, signup_end_date = utils.check_date_format(signupend)

            if not signup_end_date_checked:
                await signup_end_prompt_msg.delete()
                await signupend_msg.delete()
                error_msg = await interaction.message.channel.send(self.bot.quotes['cmdCreateCup_error_date'])
                continue

            # Check if the end date is after the start date
            if signup_start_date > signup_end_date:
                await signup_end_prompt_msg.delete()
                await signupend_msg.delete()
                error_msg = await interaction.message.channel.send(self.bot.quotes['cmdCreateCup_error_startdate'])
                signup_end_date_checked = False
                continue

        # Remove busy status
        self.bot.users_busy.remove(interaction.author.id)

        # Update db
        self.bot.db.edit_cup(id=cup_info['id'], signup_start_date=signup_start_date, signup_end_date=signup_end_date)

        # Delete msgs
        await signup_start_prompt_msg.delete()
        await signupstart_msg.delete()
        await signup_end_prompt_msg.delete()
        await signupend_msg.delete()

        # Log
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEditCupSignupDates_log'].format(cupname=cup_info['name'], oldsignupdates=f"{cup_info['signup_start_date']} to {cup_info['signup_end_date']}", newsignupdates=f"{signup_start_date} to {signup_end_date}"))

    
    async def signup(self, cup_info, user, user_info, is_admin, interaction):

        # List clans owned by the player
        clans_unfiltered = self.bot.db.get_teams_of_player(user_info['id'])

        # Not captain of any clan
        if not clans_unfiltered:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEditClan_error_notcaptain'])
            return

        # Filter out team already signed up 
        clans = []
        for clan in clans_unfiltered:
            if self.bot.db.get_clan_signup(clan['id'], cup_info['id']):
                continue
            else:
                clans.append(clan)

        if len(clans) == 0:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_alreadysignedup'])
            return

        # Get which clan to edit
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which clan do you want to signup?", components=dropmenus.teams(clans, None,  "dropmenu_teamtosignup"))
        interaction_signupteam = await self.bot.wait_for("select_option", check = lambda i: i.user.id == user.id and i.parent_component.id == "dropmenu_teamtosignup")
        clan_tosignup = clans[int(interaction_signupteam.component[0].value)]

        # Check if the roster is sufficient
        players_of_team = self.bot.db.get_active_team_players(clan_tosignup['id'])
        if len(players_of_team) < cup_info['mini_roster']:
            await interaction_signupteam.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_error_miniroster'].format(mini_roster=cup_info['mini_roster']))
            return
        elif len(players_of_team) > cup_info['maxi_roster']:
            await interaction_signupteam.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_error_maxiroster'].format(maxi_roster=cup_info['maxi_roster']))
            return

        # Check if there are any already registered members
        clans_registered = self.bot.db.get_cup_signups(cup_info['id'])
        overlapping_player_list_string = ""
        for clan_registered in clans_registered:
            # Get clan roster
            clan_roster_list = self.bot.db.get_active_team_players(clan_registered['id'])
            for player_in_roster in clan_roster_list:
                if player_in_roster in players_of_team:
                    # Get player info
                    overlapping_player_info = self.bot.db.get_player(id=player_in_roster['player_id'])
                    if len(overlapping_player_list_string) > 0:
                        overlapping_player_list_string += ", "
                    overlapping_player_list_string += overlapping_player_info['ingame_name']
        if len(overlapping_player_list_string) > 0:
            await interaction_signupteam.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_error_overlap'].format(overlap=overlapping_player_list_string))
            return            

        # Ask confirmation
        await interaction_signupteam.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_confirmation'].format(teamname=clan_tosignup['name'], cupname=cup_info['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_signupteam_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_signupteam_no"),]])
        interaction_signupteamconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_signupteam_"))

        if interaction_signupteamconfirmation.component.id == 'button_signupteam_no':
            await interaction_signupteamconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_cancel'])
            return
        
        if interaction_signupteamconfirmation.component.id == 'button_signupteam_yes':
            # Signup the clan and notify
            self.bot.db.signup_clan(clan_tosignup['id'], cup_info['id'])

            ftw_client: FTWClient = self.bot.ftw
            await ftw_client.cup_add_team(clan_tosignup['ftw_team_id'], cup_info['ftw_cup_id'])

            await interaction_signupteamconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_success'].format(teamname=clan_tosignup['name'], cupname=cup_info['name']))

            # Update log
            log_channel = discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdSignup_log'].format(teamname=clan_tosignup['name'], cupname=cup_info['name']))

    async def create_division(self, cup_info, user, user_info, is_admin, interaction):

        # Get how many divisions have been created
        divisions = self.bot.db.get_cup_divisions(cup_info['id'])
        div_number = len(divisions) + 1

        # Create div match schedule category
        category_match_schedule = await self.guild.create_category_channel(f"\U0001F4C5┋{cup_info['name']}┋D{div_number} Round1->6")

        # Create archive category
        category_archive = await self.guild.create_category_channel(f"\U0001F4BC┋Archives┋D{div_number}")

        # Add division in the DB
        self.bot.db.create_division(div_number, cup_info['id'], category_match_schedule.id, category_archive.id)

        # Add division edit message in the admin channel
        chan_admin = discord.utils.get(self.guild.channels, id=int(cup_info['chan_admin_id']))
        await chan_admin.send(f"Commands to edit the division {div_number}", components=[[
                                    Button(style=ButtonStyle.green, label="Add a team", custom_id=f"button_add_team_div_{div_number}"),
                                    Button(style=ButtonStyle.blue, label="Remove a team", custom_id=f"button_remove_team_div_{div_number}"),
                                    Button(style=ButtonStyle.blue, label="Create fixtures for entire division", custom_id=f"button_create_fixtures_div_{div_number}")
                                ],
                                [
                                    Button(style=ButtonStyle.blue, label="Fix Points", custom_id=f"button_fixpoints_{div_number}"),
                                    Button(style=ButtonStyle.red, label="Delete division", custom_id=f"button_delete_div_{div_number}")
                                ]])

        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"Div {div_number} created.")


    async def add_team_division(self, cup_info, user, user_info, is_admin, interaction):
        # Get the division
        div_number = interaction.component.id.split("_")[-1]

        # Get which team to add
        teams_signedup = self.bot.db.get_teams_nodiv_from_cup(cup_info['id'])

        if not teams_signedup:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="No teams to add")
            return

        team_to_add_dropmenu = dropmenus.teams(teams_signedup, "Select a team", f"dropmenu_team_to_add_{div_number}") 
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"Which team do you want to add to the ``division {div_number}``?", components=team_to_add_dropmenu)
        interaction_team_to_add_div = await self.bot.wait_for("select_option", check = lambda i: i.user.id == user.id and i.parent_component.id == f"dropmenu_team_to_add_{div_number}")
        team_to_add = teams_signedup[int(interaction_team_to_add_div.component[0].value)]

        # Ask confirmation
        await interaction_team_to_add_div.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddTeamDiv_confirmation'].format(teamname=team_to_add['name'], div_number=div_number), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_addteamdiv_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_addteamdiv_no"),]])
        interaction_addteamdivconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_addteamdiv_"))

        if interaction_addteamdivconfirmation.component.id == 'button_addteamdiv_no':
            await interaction_addteamdivconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddTeamDiv_cancel'])
            return
        
        if interaction_addteamdivconfirmation.component.id == 'button_addteamdiv_yes':
            # Insert team into table
            self.bot.db.edit_signups(cup_info['id'], team_to_add['id'], div_number)

            ftw_client: FTWClient = self.bot.ftw
            await ftw_client.cup_set_team_division(cup_info['ftw_cup_id'], team_to_add['ftw_team_id'], div_number)

            # Notify and  log
            await interaction_addteamdivconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddTeamDiv_success'].format(teamname=team_to_add['name'], div_number=div_number))
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdAddTeamDiv_log'].format(teamname=team_to_add['name'], div_number=div_number, cupname=cup_info['name']))

    async def remove_team_division(self, cup_info, user, user_info, is_admin, interaction):
        # Get the division
        div_number = interaction.component.id.split("_")[-1]

        # Get which team to remove
        teams_in_div = self.bot.db.get_cup_signups(cup_info['id'], div_number)

        if not teams_in_div:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="No teams to remove")
            return

        team_to_remove_dropmenu = dropmenus.teams(teams_in_div, "Select a team", f"dropmenu_team_to_remove_{div_number}") 
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"Which team do you want to remove from the ``division {div_number}``?", components=team_to_remove_dropmenu)
        interaction_team_to_remove_div = await self.bot.wait_for("select_option", check = lambda i: i.user.id == user.id and i.parent_component.id == f"dropmenu_team_to_remove_{div_number}")
        team_to_remove = teams_in_div[int(interaction_team_to_remove_div.component[0].value)]

        # Ask confirmation
        await interaction_team_to_remove_div.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdRemoveTeamDiv_confirmation'].format(teamname=team_to_remove['name'], div_number=div_number), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_removeteamdiv_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_removeteamdiv_no"),]])
        interaction_addteamdivconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_removeteamdiv_"))

        if interaction_addteamdivconfirmation.component.id == 'button_removeteamdiv_no':
            await interaction_addteamdivconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddTeamDiv_cancel'])
            return
        
        if interaction_addteamdivconfirmation.component.id == 'button_removeteamdiv_yes':
            # Remove team from div
            self.bot.db.edit_signups(cup_info['id'], team_to_remove['id'], div_number=0)

            ftw_client: FTWClient = self.bot.ftw
            await ftw_client.cup_set_team_division(cup_info['ftw_cup_id'], team_to_remove['ftw_team_id'], None)

            # Notify and  log
            await interaction_addteamdivconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdRemoveTeamDiv_success'].format(teamname=team_to_remove['name'], div_number=div_number))
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdRemoveTeamDiv_log'].format(teamname=team_to_remove['name'], div_number=div_number, cupname=cup_info['name']))

    async def fix_points_division(self, cup_info, user, user_info, is_admin, interaction):
        # Get the division
        div_number = interaction.component.id.split("_")[-1]

        # Get which team to edit
        teams_in_div = self.bot.db.get_teams_in_div(self, cup_info['id'], div_number)

        if not teams_in_div:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="No teams to edit")
            return

        team_to_edit_dropmenu = dropmenus.teams(teams_in_div, "Select a team", f"dropmenu_team_to_edit_{div_number}") 
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=f"For which team do you want to change the points?", components=team_to_edit_dropmenu)
        interaction_team_to_edit = await self.bot.wait_for("select_option", check = lambda i: i.user.id == user.id and i.parent_component.id == f"dropmenu_team_to_edit_{div_number}")
        team_to_edit = teams_in_div[int(interaction_team_to_edit.component[0].value)]

        # Ask confirmation
        await interaction_team_to_edit.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdFixPoints_confirmation'].format(teamname=team_to_edit['name'], div_number=div_number), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_editpoints_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_editpoints_no"),]])
        interaction_addteamdivconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_editpoints_"))

        if interaction_addteamdivconfirmation.component.id == 'button_editpoints_no':
            await interaction_addteamdivconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddTeamDiv_cancel'])
            return
        
        if interaction_addteamdivconfirmation.component.id == 'button_editpoints_yes':

            # Flag the user as busy
            self.bot.users_busy.append(interaction.author.id)

            await interaction_addteamdivconfirmation.respond(type=6)

            def check(m):
                return m.author == interaction.author and m.channel == interaction.message.channel

            # Wait for new W/D/L and check validity
            wdl_checked = False
            error_msg = None
            while not wdl_checked:
                prompt_msg = await interaction.message.channel.send(self.bot.quotes['cmdFixPoints_prompt'])
                wdl_msg = await self.bot.wait_for('message', check=check)
                wdl = wdl_msg.content.lower().strip()

                # Delete error message if any
                try:
                    await error_msg.delete()
                except:
                    pass

                # Cancel 
                if wdl.lower() == '!cancel':
                    await prompt_msg.delete()
                    await wdl_msg.delete()
                    # Remove busy status
                    self.bot.users_busy.remove(interaction.author.id)
                    return

                wdl_elements = wdl.split('/')
                if len(wdl_elements) != 3 or not wdl_elements[0].isnumeric() or not wdl_elements[1].isnumeric() or not wdl_elements[2].isnumeric():
                    await prompt_msg.delete()
                    await wdl_msg.delete()
                    error_msg = await interaction.message.channel.send(self.bot.quotes['cmdFixPoints_error'])
                    continue

                else:
                    win = int(wdl_elements[0])
                    draw = int(wdl_elements[1])
                    loss = int(wdl_elements[2])
                    points = win * 3 + draw
                    wdl_checked = True
                    # Remove busy status
                    self.bot.users_busy.remove(interaction.author.id)

            # Update points
            self.bot.db.edit_signup(cup_id=cup_info['id'], team_id=team_to_edit['id'], win=win, draw=draw, loss=loss, points=points)

            # Delete msgs
            await prompt_msg.delete()
            await wdl_msg.delete()


    async def delete_division(self, cup_info, user, user_info, is_admin, interaction):
        # Get the division
        div_number = interaction.component.id.split("_")[-1]

        # Ask confirmation
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeleteDiv_confirmation'].format(div_number=div_number), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_deletediv_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_deletediv_no"),]])
        interaction_deletedivconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_deletediv_"))

        if interaction_deletedivconfirmation.component.id == 'button_deletediv_no':
            await interaction_deletedivconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddTeamDiv_cancel'])
            return
        
        if interaction_deletedivconfirmation.component.id == 'button_deletediv_yes':
            await interaction_deletedivconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeleteDiv_success'].format(div_number=div_number))

            # Delete div embed
            div_to_delete = self.bot.db.get_division(div_number=div_number, cup_id=cup_info['id'])
            signup_channel = discord.utils.get(self.guild.channels, id=int(cup_info['chan_stage_id']))
            division_message = await signup_channel.fetch_message(div_to_delete['embed_id'])
            await division_message.delete()

            # Delete control panel message
            await interaction.message.delete()

            # Delete div from div table
            self.bot.db.delete_division(cup_info['id'], div_number)

            # Delete div from signups
            teams_in_div = self.bot.db.get_teams_in_div(self, cup_info['id'], div_number)
            
            for team_in_div in teams_in_div:
                # Remove team from div
                self.bot.db.edit_signup(cup_info['id'], team_in_div['id'], div_number=0, win=0, draw=0, loss=0, points=0)

            # Notify and  log
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdDeleteDiv_log'].format(div_number=div_number, cupname=cup_info['name']))




def setup(bot):
    bot.add_cog(Cups(bot))