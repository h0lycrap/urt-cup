import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check
import cogs.common.dropmenus as dropmenus
import datetime

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Cups(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        user = discord.utils.get(self.guild.members, id=interaction.user.id)
        # Get user info
        self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id = %s;", (user.id,))
        user_info = self.bot.cursor.fetchone()

        if interaction.component.id.startswith("button_signup_"):
            # Get the clan to edit
            cup_id = interaction.component.id.split("_")[-1]
            is_admin = interaction.component.id.split("_")[-2] == "admin"

            # Get cup info
            self.bot.cursor.execute("SELECT * FROM Cups WHERE id=%s", (cup_id,))
            cup_info = self.bot.cursor.fetchone()

            await self.signup(cup_info, user, user_info, is_admin, interaction)

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

        # Wait for minimym number of players per roster and check validity
        number_of_miniroster_checked = False
        while not number_of_miniroster_checked:
            await ctx.send(self.bot.quotes['cmdCreateCup_prompt_miniroster'])
            number_of_miniroster_msg = await self.bot.wait_for('message', check=check)
            mini_roster = number_of_miniroster_msg.content.lower().strip()

            if not mini_roster.isnumeric():
                await ctx.send(self.bot.quotes['cmdCreateCup_error_nbofteams'])

            # Cancel 
            if mini_roster.lower() == '!cancel':
                await ctx.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(ctx.author.id)
                return

            else:
                mini_roster = int(mini_roster)
                number_of_miniroster_checked = True


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

        self.bot.cursor.execute("INSERT INTO Cups (name, number_of_teams, mini_roster, signup_start_date, signup_end_date) VALUES (%s, %d, %d,  %s, %s)", (name, number_of_teams, mini_roster, signup_start_date, signup_end_date))
        cup_id = self.bot.cursor.lastrowid
        self.bot.conn.commit()

        # Print log
        await ctx.channel.send(self.bot.quotes['cmdCreateCup_success'])

        # Update signup ctx
        await update.signups(self.bot)

    
    async def signup(self, cup_info, user, user_info, is_admin, interaction):

        # List clans owned by the player
        self.bot.cursor.execute("SELECT * FROM Teams WHERE captain = %s;", (user_info['id'],))
        clans_unfiltered = self.bot.cursor.fetchall()

        # Not captain of any clan
        if not clans_unfiltered:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEditClan_error_notcaptain'])
            return

        # Filter out team already signed up 
        clans = []
        for clan in clans_unfiltered:
            self.bot.cursor.execute("SELECT * FROM Signups WHERE team_id=%s AND cup_id=%s", (clan['id'], cup_info['id']))
            if self.bot.cursor.fetchone():
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
        self.bot.cursor.execute("SELECT player_id FROM Roster WHERE team_id=%s AND (accepted= 1 OR accepted = 2)", (clan_tosignup['id'],))
        players_of_team = self.bot.cursor.fetchall()
        if len(players_of_team) < cup_info['mini_roster']:
            await interaction_signupteam.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_error_miniroster'].format(mini_roster=cup_info['mini_roster']))
            return

        # Check if there are any already registered members
        self.bot.cursor.execute("SELECT * FROM Signups WHERE cup_id=%s", (cup_info['id'],))
        clans_registered = self.bot.cursor.fetchall()
        overlapping_player_list_string = ""
        for clan_registered in clans_registered:
            # Get clan roster
            self.bot.cursor.execute("SELECT player_id FROM Roster WHERE team_id=%s AND (accepted= 1 OR accepted = 2)", (clan_registered['team_id'],))
            clan_roster_list = self.bot.cursor.fetchall()
            for player_in_roster in clan_roster_list:
                if player_in_roster in players_of_team:
                    # Get player info
                    self.bot.cursor.execute("SELECT * FROM Users WHERE id=%s", (player_in_roster['player_id'],))
                    overlapping_player_info = self.bot.cursor.fetchone()
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
            self.bot.cursor.execute("INSERT INTO Signups (cup_id, team_id) VALUES (%d, %s);", (cup_info['id'], clan_tosignup['id']))
            self.bot.conn.commit()
            await interaction_signupteamconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdSignup_success'].format(teamname=clan_tosignup['name'], cupname=cup_info['name']))

            # Update signups and log
            await update.signups(self.bot)
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdSignup_log'].format(teamname=clan_tosignup['name'], cupname=cup_info['name']))

def setup(bot):
    bot.add_cog(Cups(bot))