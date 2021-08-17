import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Fixtures(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.command() 
    async def fixture(self, ctx):
        self.bot.cursor.execute("SELECT * FROM Cups;")
        cups = self.bot.cursor.fetchall()

        cup_name_list_str = ""
        for (i, cup_info) in enumerate(cups):
            index_str = (str(i + 1) + ".").ljust(2)
            cup_name_list_str += f"``{index_str}`` {cup_info['name']}\n"

        # Create cup list embed
        embed = discord.Embed(title=f"For which cup do you want to create the fixture?", color=0xFFD700)
        embed.add_field(name="Cup", value= cup_name_list_str, inline=True)
        cup_list_message = await ctx.channel.send(embed=embed)

        applied_reaction_emojis = []
        for i, cup_info in enumerate(cups):
            await cup_list_message.add_reaction(self.bot.number_emojis[i])
            applied_reaction_emojis.append(self.bot.number_emojis[i].name)

        # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
        def check_reaction(reaction, user):
                return user.id == ctx.author.id and reaction.message == cup_list_message and reaction.emoji.name in applied_reaction_emojis
        reaction, _ = await self.bot.wait_for('reaction_add', check=check_reaction)

        # Get the choice
        cup_choice = applied_reaction_emojis.index(reaction.emoji.name)
        cup_toedit = cups[cup_choice]

        # List clans signed up in the cup
        self.bot.cursor.execute("SELECT * FROM Signups WHERE cup_id = %s;", (cup_toedit['id'],))
        teams_signed_up  = self.bot.cursor.fetchall()

        if not teams_signed_up:
            await ctx.channel.send("No team signed up for this cup")
            return

        # Get clan info list
        clan_info_list = []
        for team_signed_up in teams_signed_up:

            self.bot.cursor.execute("SELECT * FROM Teams WHERE tag = %s;", (team_signed_up['team_tag'],))
            clan_info = self.bot.cursor.fetchone()
            clan_info_list.append(clan_info)

        # First clan
        team1 = await embeds.team_list(self.bot, clan_info_list, "First clan?", ctx)
        clan_info_list.remove(team1)

        # Second clan
        team2 = await embeds.team_list(self.bot, clan_info_list, "Second clan?", ctx)

        # Select if BO1 or BO2 or BO3 or BO5 or BO7
        # TODO: maybe put this in a table in the DB
        formats = ['BO1', 'BO2', 'BO3', 'BO5']
        embed = discord.Embed(title=f"Match format?", color=0xFFD700)
        embed.add_field(name="Format", value= "``1.`` BO1 \n ``2.`` BO2 \n ``3.`` BO3 \n ``4.`` BO5", inline=True)
        fixture_format_message = await ctx.channel.send(embed=embed)

        applied_reaction_emojis = []
        for i in range(4):
            await fixture_format_message.add_reaction(self.bot.number_emojis[i])
            applied_reaction_emojis.append(self.bot.number_emojis[i].name)

        # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
        def check_reaction(reaction, user):
                return user.id == ctx.author.id and reaction.message == fixture_format_message and reaction.emoji.name in applied_reaction_emojis
        reaction, _ = await self.bot.wait_for('reaction_add', check=check_reaction)

        # Get the choice
        format_choice = applied_reaction_emojis.index(reaction.emoji.name)
        fixture_format = formats[format_choice]


        # Get different roles that will have access to the channel
        role_team1 = discord.utils.get(self.guild.roles, id=int(team1['role_id'])) 
        role_team2 = discord.utils.get(self.guild.roles, id=int(team2['role_id'])) 
        role_flawless_crew = discord.utils.get(self.guild.roles, id=int(self.bot.role_flawless_crew_id)) 
        role_cup_supervisor = discord.utils.get(self.guild.roles, id=int(self.bot.role_cup_supervisor_id)) 

        # Set the permissions
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.guild.me: discord.PermissionOverwrite(read_messages=True),
            role_team1: discord.PermissionOverwrite(read_messages=True),
            role_team2: discord.PermissionOverwrite(read_messages=True),
            role_flawless_crew: discord.PermissionOverwrite(read_messages=True),
            role_cup_supervisor: discord.PermissionOverwrite(read_messages=True)
        }

        # Create text channel
        fixture_category = discord.utils.get(self.guild.channels, id=self.bot.category_match_schedule_id) 
        fixture_channel = await self.guild.create_text_channel(f"abcd┋{team1['tag']} vs {team2['tag']}", overwrites=overwrites, category=fixture_category)

        

        self.bot.cursor.execute("INSERT INTO Fixtures (cup_id, team1, team2, format, channel_id) VALUES (%d, %s, %s, %s, %s)", (cup_toedit['id'], team1['tag'], team2['tag'], fixture_format, str(fixture_channel.id)))
        self.bot.conn.commit()

        # Send fixture card
        fixture_id = self.bot.cursor.lastrowid
        embed = embeds.fixture(self.bot, fixture_id)
        fixture_card = await fixture_channel.send(embed=embed)

        self.bot.cursor.execute("UPDATE Fixtures SET embed_id=%s WHERE id = %d", (str(fixture_card.id), fixture_id))
        self.bot.conn.commit()

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

def setup(bot):
    bot.add_cog(Fixtures(bot))
