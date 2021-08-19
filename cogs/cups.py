import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import datetime

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Cups(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.command() # TODO FORMAT ARGUMENT AND MAKE ADMIN
    async def createcup(self, ctx):
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        # Check permissions
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.channel.send(self.bot.quotes['cmdCreateCup_error_perm'])
            return

        # Wait for cup name
        await ctx.channel.send(self.bot.quotes['cmdCreateCup_prompt_name'])
        name_msg = await self.bot.wait_for('ctx', check=check)
        name = name_msg.content.strip()

        # Cancel 
        if name.lower() == '!cancel':
            await ctx.channel.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
            return

        # Wait for number of teams and check validity
        number_of_teams_checked = False
        while not number_of_teams_checked:
            await ctx.channel.send(self.bot.quotes['cmdCreateCup_prompt_nbofteams'])
            number_of_teams_msg = await self.bot.wait_for('ctx', check=check)
            number_of_teams = number_of_teams_msg.content.lower().strip()

            if not number_of_teams.isnumeric():
                await ctx.channel.send(self.bot.quotes['cmdCreateCup_error_nbofteams'])
            else:
                number_of_teams = int(number_of_teams)
                number_of_teams_checked = True


        # Wait for signup start date and check validity
        signup_start_date_checked = False
        while not signup_start_date_checked:
            await ctx.channel.send(self.bot.quotes['cmdCreateCup_prompt_signupstart'])
            signupstart_msg = await self.bot.wait_for('ctx', check=check)
            signupstart = signupstart_msg.content.lower().strip()

            # Cancel 
            if signupstart == '!cancel':
                await ctx.channel.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
                return

            signup_start_date_checked, signup_start_date = utils.check_date_format(signupstart)

            if not signup_start_date_checked:
                await ctx.channel.send(self.bot.quotes['cmdCreateCup_error_date'])

        # Wait for signup end date and check validity
        signup_end_date_checked = False
        while not signup_end_date_checked:
            await ctx.channel.send(self.bot.quotes['cmdCreateCup_prompt_signupend'])
            signupend_msg = await self.bot.wait_for('ctx', check=check)
            signupend = signupend_msg.content.lower().strip()

            # Cancel 
            if signupend == '!cancel':
                await ctx.channel.send(self.bot.quotes['cmdCreateCup_prompt_cancel'])
                return

            signup_end_date_checked, signup_end_date = utils.check_date_format(signupend)

            if not signup_end_date_checked:
                await ctx.channel.send(self.bot.quotes['cmdCreateCup_error_date'])
                continue

            # Check if the end date is after the start date
            if signup_start_date > signup_end_date:
                await ctx.channel.send(self.bot.quotes['cmdCreateCup_error_startdate'])
                signup_end_date_checked = False
                continue

        self.bot.cursor.execute("INSERT INTO Cups (name, number_of_teams, signup_start_date, signup_end_date) VALUES (%s, %d, %s, %s)", (name, number_of_teams, signup_start_date, signup_end_date))
        cup_id = self.bot.cursor.lastrowid
        self.bot.conn.commit()

        # Print log
        await ctx.channel.send(self.bot.quotes['cmdCreateCup_success'])

        # Update signup ctx
        await update.signups(self.bot)

    @commands.command() # TODO FORMAT ARGUMENT AND MAKE ADMIN
    async def signup(self, ctx):

        def check(m):
                return m.author == ctx.author and m.guild == None

        self.bot.cursor.execute("SELECT * FROM Cups;")
        cup_infos = self.bot.cursor.fetchall()

        # List all cups open for signup
        # TODO: Maybe refactor this to use cup status
        cups_open =[]
        for cup_info in cup_infos:
            signup_start_date = datetime.datetime.strptime(cup_info['signup_start_date'], '%Y-%m-%d %H:%M:%S')
            signup_end_date = datetime.datetime.strptime(cup_info['signup_end_date'], '%Y-%m-%d %H:%M:%S')

            # Check if the signup are open
            if not(signup_start_date <= ctx.created_at <= signup_end_date):
                continue

            # Check if cup is full
            self.bot.cursor.execute("SELECT team_tag FROM Signups WHERE cup_id=%d", (cup_info['id'],))
            teams_signedup = self.bot.cursor.fetchall()
            if len(teams_signedup) >= cup_info['number_of_teams']:
                continue

            cups_open.append(cup_info)


        # Print all cups available
        if len(cups_open) == 0:
            await ctx.author.send(self.bot.quotes['cmdSignup_nocup'])
            return

        await ctx.author.send(self.bot.quotes['cmdSignup_intro'])
        for (i, cup_open_info) in enumerate(cups_open):
            embed = embeds.signup(self.bot, cup_open_info['id'])
            await ctx.author.send(content=str(i+1), embed=embed)

        # Wait for choice and check validity
        choice_checked = False
        while not choice_checked:
            await ctx.author.send(self.bot.quotes['cmdSignup_prompt_choice'])
            choice_msg = await self.bot.wait_for('ctx', check=check)
            choice = choice_msg.content.strip()

            # Cancel 
            if choice.lower() == '!cancel':
                await ctx.author.send(self.bot.quotes['cmdSignup_cancel'])
                return

            # Check if choice is a number and in the possible range
            if choice.isnumeric() and 1 <= int(choice) <= len(cups_open):
                choice_checked = True
            else:
                await ctx.author.send(self.bot.quotes['cmdSignup_error_choice'])
        cup_choice = cups_open[int(choice)-1] 


        # Wait for clan tag and check if it exists
        tag_checked = False
        while not tag_checked:
            await ctx.author.send(self.bot.quotes['cmdSignup_prompt_tag'].format(cupname=cup_choice['name']))
            tag_msg = await self.bot.wait_for('ctx', check=check)
            tag = tag_msg.content.strip()
            tag_str = utils.prevent_discord_formating(tag)

            # Cancel 
            if tag.lower() == '!cancel':
                await ctx.author.send(self.bot.quotes['cmdSignup_cancel'])
                return

            # Check if the team exist
            self.bot.cursor.execute("SELECT * FROM Teams WHERE tag = %s;", (tag,)) 
            team_toedit = self.bot.cursor.fetchone()
            if not team_toedit:
                await ctx.author.send(self.bot.quotes['cmdSignup_error_tagnotexist'])
                continue
                
            # Check if the user is the captain of the clan
            if team_toedit['captain'] != str(ctx.author.id):
                await ctx.author.send(self.bot.quotes['cmdSignup_error_notcaptain'])
                continue

            tag_checked = True

        # Signup the clan and notify
        self.bot.cursor.execute("INSERT INTO Signups (cup_id, team_tag) VALUES (%d, %s);", (cup_choice['id'], tag))
        self.bot.conn.commit()
        await ctx.author.send(self.bot.quotes['cmdSignup_success'].format(teamtag=tag_str, cupname=cup_choice['name']))

        # Update signups and log
        await update.signups(self.bot)
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdSignup_log'].format(teamtag=tag_str, cupname=cup_choice['name']))

def setup(bot):
    bot.add_cog(Cups(bot))