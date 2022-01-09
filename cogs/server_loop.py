import discord
from discord import channel
from discord.ext import commands, tasks
from cogs.common.enums import FixtureStatus
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check
import cogs.common.dropmenus as dropmenus
import flag
import datetime
import bs4
import requests

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component, interaction

class ServerLoop(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]
        self.Loop.start()


    @tasks.loop(seconds=3600)
    async def Loop(self):
        # Do some updates
        self.bot.async_loop.create_task(update.roster(self.bot))
        self.bot.async_loop.create_task(update.signups(self.bot))
        self.bot.async_loop.create_task(update.fixtures(self.bot))

        await self.check_upload_status()
        await self.refresh_all_fixture_status()
        print("Loop!")

    # TODO: MOVE THIS TO ANOTHER COG FILE
    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        user = discord.utils.get(self.guild.members, id=interaction.user.id)

        if interaction.component.id.startswith("button_problem_"):
            # Get fixture
            fixture_id = interaction.component.id.split("_")[-1]
            fixture = self.bot.db.get_fixture(id=fixture_id)
            await self.refresh_fixture_status(interaction.message, fixture)

            if interaction.component.id.startswith("button_problem_fixed"):
                await self.fix_fixture(interaction, fixture)
            elif interaction.component.id.startswith("button_problem_refresh"):
                await interaction.respond(type=6)
            elif interaction.component.id.startswith("button_problem_dm"):
                await self.dm_players(interaction, fixture)



    async def check_upload_status(self):
        # Get all fixtures with status completed
        fixtures = self.bot.db.get_fixtures_of_status(FixtureStatus.Finished)

        for fixture in fixtures:
            # Get fixture problems
            problems, deltahours, _, _ = self.get_fixture_problems(fixture)
            
            if problems == "":
                #Archive
                await self.archive_fixture(fixture)
                continue

            # Only post if it has been more than 50 since the game was played 
            #if deltahours < 50:
            #    continue

            # Update fixture status to missing files
            self.bot.db.edit_fixture(fixture['id'], status=FixtureStatus.ScoresEntered)

            # Post to the demo log channel
            demolog_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_demolog_id)
            await demolog_channel.send(problems, components=[[
                Button(style=ButtonStyle.blue, label="Refresh", custom_id=f"button_problem_refresh_{fixture['id']}"),
                Button(style=ButtonStyle.gray, label="DM Players: 0", custom_id=f"button_problem_dm_{fixture['id']}"),
                Button(style=ButtonStyle.green, label="Fix", custom_id=f"button_problem_fixed_{fixture['id']}")
            ]])


    async def archive_fixture(self, fixture):
        # Update fixture status to archived
        self.bot.db.edit_fixture(fixture['id'], status=FixtureStatus.Archived)

        # Get div number
        fixture_channel = discord.utils.get(self.guild.channels, id=int(fixture['channel_id']))
        if "D1" in fixture_channel.category.name:
            div_number = 1
        else:
            div_number = 2 

        # Get div info
        div_info = self.bot.db.get_division(cup_id=fixture['cup_id'], div_number=div_number)

        # Archive fixture channel
        archive_category = discord.utils.get(self.guild.categories, id=int(div_info['archive_category_id']))

        # Check if category is full
        if len(archive_category.channels) >= 50:
            archive_category = await self.guild.create_category_channel(f"\U0001F4BC┋Archives┋D{div_number}")
            self.bot.db.edit_division(id=div_info['id'], archive_category_id=archive_category.id)

        await fixture_channel.edit(category=archive_category)

    def get_fixture_problems(self, fixture):
        # Get all the players that played
        playersPlayed = self.bot.db.get_fixture_players(fixture_id=fixture['id'])

        # Get teams info
        team1_info = self.bot.db.get_clan(id=fixture['team1'])
        team2_info = self.bot.db.get_clan(id=fixture['team2'])

        # Get maps info
        maps_played = self.bot.db.get_fixture_maps(fixture_id=fixture['id'])

        # Get the number of hours since the game was played
        gamedate = datetime.date.fromisoformat(fixture['date'].split()[0])
        gametime = datetime.time.fromisoformat(fixture['date'].split()[1])
        gameschedule = datetime.datetime.combine(gamedate, gametime)

        deltatime = datetime.datetime.now() - gameschedule
        deltahours = deltatime.days * 24 + deltatime.seconds / 3600

        if deltahours >= 50:
            hours_str = f":warning: **{int(deltahours)}h**"
        else:
            hours_str = f"**{int(deltahours)}h**"

        problems_team1 = ""
        problems_team2 = ""
        problem_list = []
        dm_info = [] # almost similar to problem_list but if both demo and moss are missing, they are grouped
        for playerPlayed in playersPlayed:
            # Check if moss and demos were uploaded previously
            if int(playerPlayed['uploaded_moss']) and int(playerPlayed['uploaded_demo']):
                continue

            # There is a pb, get player and team info
            playerteam_info = self.bot.db.get_clan_player_from_fixture(playerPlayed['player_id'], fixture['team1'], fixture['team2'])

            if not playerteam_info:
                print(playerPlayed, fixture)
                continue

            uploads = bs4.BeautifulSoup(requests.get(f"https://urt.li/ac-flawless/{playerteam_info['urt_auth']}/{fixture['date']}/", auth=requests.auth.HTTPBasicAuth(self.bot.urtli_id, self.bot.urtli_pass)).text, features="lxml") 
            demos = [upload["href"] for upload in uploads.find_all("a") if upload["href"].endswith(".urtdemo") or upload["href"].endswith(".dm_68")]
            moss = [upload["href"] for upload in uploads.find_all("a") if upload["href"].endswith(".zip")]

            all_demos = "".join(demos)
            missing_demos = ""
            # Check demos
            for map in maps_played:
                if not map['name'].lower() in all_demos:
                    missing_demos += f"{map['name']} __{map['gamemode']}__ "

            demoOk = missing_demos == "" or int(playerPlayed['uploaded_demo'])
            mossOk = len(moss) > 0 or int(playerPlayed['uploaded_moss'])

            # Update db
            if mossOk and not int(playerPlayed['uploaded_moss']):
                self.bot.db.edit_fixture_player(player_id=playerPlayed['player_id'], fixture_id=fixture['id'], uploaded_moss=1)
            if demoOk and not int(playerPlayed['uploaded_demo']):
                self.bot.db.edit_fixture_player(player_id=playerPlayed['player_id'], fixture_id=fixture['id'], uploaded_demo=1)

            if mossOk and demoOk:
                continue

            # Append the problem message
            if not mossOk and not demoOk:
                problem_msg  = f'**Demos** ({missing_demos}) and **Moss**' 
                problem_list.append([playerteam_info['urt_auth'], 'Moss'])
                problem_list.append([playerteam_info['urt_auth'], 'Demo'])

                dm_info.append([playerteam_info['discord_id'], f'**Demos** ({missing_demos}) and **Moss**'])
            elif not mossOk:
                problem_msg  = '**Moss**'
                problem_list.append([playerteam_info['urt_auth'], 'Moss'])

                dm_info.append([playerteam_info['discord_id'], '**Moss**'])
            else:
                problem_msg  = f'**Demos** ({missing_demos})'
                problem_list.append([playerteam_info['urt_auth'], 'Demo'])

                dm_info.append([playerteam_info['discord_id'], f'**Demos** ({missing_demos})'])

            if int(playerteam_info['team_id']) == int(fixture['team1']):
                problems_team1 += f"- ``{playerteam_info['urt_auth']}``: {problem_msg} \n"
            else:
                problems_team2 += f"- ``{playerteam_info['urt_auth']}``: {problem_msg} \n"
            
        if problems_team1 == "" and problems_team2 == "":
            problems = ""

        else:
            problems = f"{hours_str} \u200b \u200b **|** \u200b \u200b Missing files for the fixture <#{fixture['channel_id']}>\n"
            if problems_team1 != "":
                problems += f"\n:small_blue_diamond: {utils.prevent_discord_formating(team1_info['tag'])}\n" + problems_team1
            if problems_team2 != "":
                problems += f"\n:small_blue_diamond: {utils.prevent_discord_formating(team2_info['tag'])}\n" + problems_team2

        return problems, deltahours, problem_list, dm_info

    async def refresh_fixture_status(self, message, fixture, dm=False):
        # Get fixture problems
        problems, _, _, _ = self.get_fixture_problems(fixture)
        
        if problems == "":
            #Archive
            await self.archive_fixture(fixture)

            # Delete message
            await message.delete()
            return

        # Get the current dm counter and increment if needed
        dm_counter = int(message.components[0][1].label[-1])
        if dm:
            dm_counter +=1

        # Update message
        await message.edit(problems, components=[[
            Button(style=ButtonStyle.blue, label="Refresh", custom_id=f"button_problem_refresh_{fixture['id']}"),
            Button(style=ButtonStyle.gray, label=f"DM Players: {dm_counter}", custom_id=f"button_problem_dm_{fixture['id']}"),
            Button(style=ButtonStyle.green, label="Fix", custom_id=f"button_problem_fixed_{fixture['id']}")
        ]])

        

    async def fix_fixture(self, interaction, fixture):
        # Get fixture problems
        problems, _, problem_list, _ = self.get_fixture_problems(fixture)

        dropmenu_problem = dropmenus.problems(problem_list, "dropmenu_problems")

        # Get which problem to fix
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which problem do you want to fix?", components=dropmenu_problem)
        interaction_fixproblem = await self.bot.wait_for("select_option", check = lambda i: i.user.id == interaction.author.id and i.parent_component.id == "dropmenu_problems")
        problem_tofix = problem_list[int(interaction_fixproblem.component[0].value)]
        problem_player = problem_tofix[0]
        problem_type = problem_tofix[1]

        # Ask confirmation
        await interaction_fixproblem.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdFixProblem_confirmation'].format(name=problem_player, type=problem_type), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_fixproblem_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_fixproblem_no"),]])
        interaction_fixproblemconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == interaction.author.id and i.component.id.startswith("button_fixproblem_"))

        if interaction_fixproblemconfirmation.component.id == 'button_fixproblem_no':
            await interaction_fixproblemconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdFixProblem_cancel'])
            return

        elif interaction_fixproblemconfirmation.component.id == 'button_fixproblem_yes':
            # Get player id
            user_info = self.bot.db.get_player(urt_auth=problem_player)

            # Set document as uploaded
            if problem_type == "Moss":
                self.bot.db.edit_fixture_player(player_id=user_info['id'], fixture_id=fixture['id'], uploaded_moss=1)
            elif problem_type == "Demo":
                self.bot.db.edit_fixture_player(player_id=user_info['id'], fixture_id=fixture['id'], uploaded_demo=1)

            # Refresh problem
            await self.refresh_fixture_status(interaction.message, fixture)

            await interaction_fixproblemconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdFixProblem_success'])

    async def refresh_all_fixture_status(self):
        # Get channel
        demolog_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_demolog_id)
        messages = await demolog_channel.history(limit=500).flatten()

        for message in messages:
            # Get fixture id (the message might not be a problem message)
            try:
                fixture_id = message.components[0][0].id.split("_")[-1]
            except:
                continue

            # Get fixture
            fixture = self.bot.db.get_fixture(id=fixture_id)

            # refresh fixture
            await self.refresh_fixture_status(message, fixture)

    async def dm_players(self, interaction, fixture):
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Started to dm players.")

        # Get fixture problems
        problems, deltahours, problem_list, dm_list = self.get_fixture_problems(fixture)

        # Get teams info
        team1_info = self.bot.db.get_clan(id=fixture['team1'])
        team2_info = self.bot.db.get_clan(id=fixture['team2'])

        players_not_on_discord = ""
        for dm in dm_list:
            # Get discord info
            player_todm = discord.utils.get(self.guild.members, id=int(dm[0]))
            if not player_todm:
                # Get missing player info
                player_info = self.bot.db.get_player(discord_id=dm[0])
                players_not_on_discord += f"``{player_info['urt_auth']}`` "
                continue

            dm_text = self.bot.quotes['cmdDM_missing_files'].format(playername=player_todm.display_name, team1=team1_info['name'], team2=team2_info['name'], problems=dm[1], deltatime= 72 - int(deltahours))
            await player_todm.send(dm_text)

        # Log problems
        if players_not_on_discord != "":
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(f"Couldn't dm the players (left discord server) : {players_not_on_discord}")

        # refresh fixture
        await self.refresh_fixture_status(interaction.message, fixture, dm=True)




def setup(bot):
    bot.add_cog(ServerLoop(bot))