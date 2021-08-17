import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import flag

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Clans(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]
        update.roster(self.bot)

    #commands.guild(None) ?
    @commands.command() # TODO: refactor to make it triggerable by a button and make it only PM
    async def createclan(self, ctx):
        # Flag the user as busy
        self.bot.users_busy.append(ctx.author.id)

        def check(m):
                return m.author == ctx.author and m.guild == None

        await ctx.author.send(self.bot.quotes['cmdCreateClan_intro'])

        # Wait for team name and check if the clan name is taken
        name_checked = False
        while not name_checked:
            await ctx.author.send(self.bot.quotes['cmdCreateClan_prompt_name'])
            teamname_msg = await self.bot.wait_for('message', check=check)
            teamname = teamname_msg.content.strip()

            # Cancel team creation
            if teamname.lower() == '!cancel':
                await ctx.author.send(self.bot.quotes['cmdCreateClan_cancel'])
                return

            self.bot.cursor.execute("SELECT id FROM Teams WHERE name = %s", (teamname,))   
            if self.bot.cursor.fetchone():
                await ctx.author.send(self.bot.quotes['cmdCreateClan_error_name'])
            else:
                name_checked = True


        # Wait for team tag and check if the team tag is taken    
        tag_checked = False
        while not tag_checked:
            await ctx.author.send(self.bot.quotes['cmdCreateClan_prompt_tag'])
            tag_msg = await self.bot.wait_for('message', check=check)
            tag = tag_msg.content.strip()

            # Cancel team creation
            if tag.lower() == '!cancel':
                await ctx.author.send(self.bot.quotes['cmdCreateClan_cancel'])
                return

            self.bot.cursor.execute("SELECT id FROM Teams WHERE tag = %s", (tag,))   
            if self.bot.cursor.fetchone():
                await ctx.author.send(self.bot.quotes['cmdCreateClan_error_tag'])
            else:
                tag_checked = True

        # Wait for team flag and check if this is a flag emoji 
        country_checked = False
        while not country_checked:
            await ctx.author.send(self.bot.quotes['cmdCreateClan_prompt_flag'])
            country_msg = await self.bot.wait_for('message', check=check)
            country, country_checked = utils.check_flag_emoji(country_msg.content.strip())

            # Cancel team creation
            if country_msg.content.strip().lower() == '!cancel':
                await ctx.author.send(self.bot.quotes['cmdCreateClan_cancel'])
                return

            if not country_checked:
                await ctx.author.send(self.bot.quotes['cmdCreateClan_error_country'])

        # Create team ds role
        team_role = await self.guild.create_role(name=tag)

        # Add team to DB
        self.bot.cursor.execute("INSERT INTO Teams(name, tag, country, captain, role_id) VALUES (%s, %s, %s, %s, %s) ;", (teamname, tag, country, ctx.author.id, team_role.id))
        self.bot.conn.commit()

        # Add captain to team roster accepted=2 means captain
        captain = discord.utils.get(self.guild.members, id=int(ctx.author.id))
        captain_role = discord.utils.get(self.guild.roles, id=int(self.bot.role_captains_id))
        await captain.add_roles(captain_role, team_role)
        self.bot.cursor.execute("INSERT INTO Roster(team_tag, player_name, accepted) VALUES (%s, %s, %d) ;", (tag, captain.display_name, 2))
        self.bot.conn.commit()

        await ctx.author.send(self.bot.quotes['cmdCreateClan_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        embed, _ = embeds.team(self.bot, tag)
        await log_channel.send(content=self.bot.quotes['cmdCreateClan_log'], embed=embed)

        # Remove busy status
        self.bot.users_busy.remove(ctx.author.id)

        # Update roster
        await update.roster()

    #commands.guild(None) ?
    @commands.command() # TODO: refactor to make it triggerable by a button and make it only PM
    async def editclan(self, ctx):  # TODO refactor to make it a drop lsit

        def check(m):
                return m.author == ctx.author and m.guild == None

        # List clans owned by the player
        self.bot.cursor.execute("SELECT * FROM Teams WHERE captain = %s;", (str(ctx.author.id),))
        clans = self.bot.cursor.fetchall()

        if not clans:
            await ctx.author.send(self.bot.quotes['cmdEditClan_error_notcaptain'])
            return

        team_toedit = await embeds.team_list(clans,"Which clan do you want to edit?", ctx)



        team_edition_finished = False
        while not team_edition_finished:
            # Show team card and display choices
            embed, _ = embeds.team(self.bot, tag=team_toedit['tag'], show_invited=True)
            await ctx.author.send(embed = embed)
            choice_message = await ctx.author.send(self.bot.quotes['cmdEditClan_intro'])

            number_of_choices = 5
            applied_reaction_emojis = []
            for i in range(number_of_choices):
                await choice_message.add_reaction(self.bot.number_emojis[i])
                applied_reaction_emojis.append(self.bot.number_emojis[i].name)

            # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
            def check_reaction(reaction, user):
                    return user.id != self.bot.user.id and reaction.message == choice_message and reaction.emoji.name in applied_reaction_emojis
            reaction, _ = await self.bot.wait_for('reaction_add', check=check_reaction)

            # Get the choice
            choice = applied_reaction_emojis.index(reaction.emoji.name) + 1


            # Commands available for team edits # TODO Refactor this
            editclan_funcs = {1: self.add_player, 2: self.delete_player, 3: self.update_team_flag, 4: self.change_clan_captain, 5: self.delete_team}

            if choice in editclan_funcs:
                # Set busy status
                self.bot.users_busy.append(ctx.author.id)

                await editclan_funcs[choice](team_toedit, ctx.author)

                # Remove busy status
                self.bot.users_busy.remove(ctx.author.id)

            if choice == '5':
                return
            
            # Ask if the user wants to keep going
            continue_message = await ctx.author.send(self.bot.quotes['cmdEditClan_prompt_continue'])
            await continue_message.add_reaction(u"\U00002705")
            await continue_message.add_reaction(u"\U0000274C")

            def check_reaction(reaction, user):
                return user.id != self.bot.user.id and reaction.message == continue_message and (str(reaction.emoji) == u"\U00002705" or str(reaction.emoji) == u"\U0000274C")

            reaction, _ = await self.bot.wait_for('reaction_add', check=check_reaction)

            # Wants to continue
            if str(reaction.emoji) == u"\U00002705":
                continue

            # Is done
            elif str(reaction.emoji) == u"\U0000274C":
                embed, _ = embeds.team(self.bot, tag=team_toedit['tag'], show_invited=True)
                await ctx.author.send(content=self.bot.quotes['cmdEditClan_continue_no'], embed=embed)
                team_edition_finished = True
            

    async def add_player(self, team_toedit, user):

        # Check if the max number of players per clan has been reached
        self.bot.cursor.execute("SELECT * FROM Roster WHERE team_tag = %s;", (team_toedit['tag'],))
        players_inclan = self.bot.cursor.fetchall()
        if len(players_inclan) >= self.bot.max_players_per_team:
            await user.send(self.bot.quotes['cmdAddPlayer_error_maxplayer'])
            return

        def check(m):
                return m.author == user and m.guild == None

        # Wait for the auth list to add
        await user.send(self.bot.quotes['cmdAddPlayer_prompt_auth'])
        
        player_msg = await self.bot.wait_for('message', check=check)
        auth_list = player_msg.content.strip().split(',')

        # Cancel 
        if player_msg.content.strip().lower() == '!cancel':
            await user.send(self.bot.quotes['cmdAddPlayer_cancel'])
            return

        # Check if we are trying to add more players than the limit
        if len(auth_list) + len(players_inclan) > self.bot.max_players_per_team:
            await user.send(self.bot.quotes['cmdAddPlayer_error_maxplayer'])
            return

        for auth in auth_list:
            auth = auth.strip()

            # Check if the auth is registered
            self.bot.cursor.execute("SELECT ingame_name, discord_id FROM Users WHERE urt_auth = %s;", (auth,))
            player_toadd = self.bot.cursor.fetchone()
            if not player_toadd:
                await user.send(self.bot.quotes['cmdAddPlayer_error_auth'].format(auth=auth))
                continue

            # Check if user was already invited
            self.bot.cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toadd['ingame_name']))
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdAddPlayer_error_alreadyinvited'].format(name=player_toadd['ingame_name']))
                continue

            # Add player to roster
            self.bot.cursor.execute("INSERT INTO Roster(team_tag, player_name) VALUES (%s, %s) ;", (team_toedit['tag'], player_toadd['ingame_name']))
            self.bot.conn.commit() 

            # Invite each player
            await user.send(self.bot.quotes['cmdAddPlayer_invitesent'].format(name=player_toadd['ingame_name'])) 
            self.bot.async_loop.create_task(self.invite_player(player_toadd, user, team_toedit))

    async def invite_player(self, player_toadd, user, team_toedit):
        # DM invite to user
        player_topm = discord.utils.get(self.guild.members, id=int(player_toadd['discord_id']))
        captain = discord.utils.get(self.guild.members, id=int(user.id)) # Assuming the bot is only on 1 server

        invite_message = await player_topm.send(self.bot.quotes['cmdAddPlayer_invite'].format(captain=captain.display_name, teamname=team_toedit['name']))
        await invite_message.add_reaction(u"\U00002705")
        await invite_message.add_reaction(u"\U0000274C") 

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdAddPlayer_invite_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

        # Wait for reaction and check if the user isnt the bot and if the reaction emojis are the correct one
        def check_reaction(reaction, user):
                return user.id != self.bot.user.id and reaction.message == invite_message and (str(reaction.emoji) == u"\U00002705" or str(reaction.emoji) == u"\U0000274C")
        reaction, _ = await self.bot.wait_for('reaction_add', check=check_reaction)

        # Check if the player was still invited
        self.bot.cursor.execute("SELECT id FROM Roster WHERE accepted=0 AND team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toadd['ingame_name']))
        if not self.bot.cursor.fetchone():
            await player_topm.send(self.bot.quotes['cmdAddPlayer_nolongerinvited'].format(teamname=team_toedit['name']))
            return

        # Accepted invite
        if str(reaction.emoji) == u"\U00002705":
            self.bot.cursor.execute("UPDATE Roster SET accepted=1 WHERE  team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toadd['ingame_name']))
            self.bot.conn.commit()

            await captain.send(self.bot.quotes['cmdAddPlayer_accepted_cap'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

            await player_topm.send(self.bot.quotes['cmdAddPlayer_accepted'].format(teamname=team_toedit['name']))
            await update.roster(self.bot)

            # Add team role to player
            team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
            await player_topm.add_roles(team_role)

            # Print on the log channel
            await log_channel.send(self.bot.quotes['cmdAddPlayer_accepted_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

        # Declined invite
        elif str(reaction.emoji) == u"\U0000274C":
            await captain.send(self.bot.quotes['cmdAddPlayer_declined_cap'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))
            self.bot.cursor.execute("DELETE FROM Roster WHERE  team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toadd['ingame_name']))
            self.bot.conn.commit()
            await player_topm.send(self.bot.quotes['cmdAddPlayer_declined'].format(teamname=team_toedit['name']))

            # Print on the log channel
            await log_channel.send(self.bot.quotes['cmdAddPlayer_declined_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))


    async def delete_player(self, team_toedit, user):

        def check(m):
                return m.author == user and m.guild == None

        # Wait for the player auth, and check if it exist
        player_checked = False
        while not player_checked:
            await user.send(self.bot.quotes['cmdDeletePlayer_prompt_auth'])
            
            player_msg = await self.bot.wait_for('message', check=check)
            auth = player_msg.content.strip() 

            # Cancel 
            if auth.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdDeletePlayer_cancel'])
                return

            # Check if the auth is registered
            self.bot.cursor.execute("SELECT ingame_name, discord_id FROM Users WHERE urt_auth = %s;", (auth,))
            player_toremove = self.bot.cursor.fetchone()
            if not player_toremove:
                await user.send(self.bot.quotes['cmdDeletePlayer_error_auth'].format(auth=auth))
                continue

            # Check if the user is trying to delete himself:
            if player_toremove['discord_id'] == str(user.id):
                await user.send(self.bot.quotes['cmdDeletePlayer_error_self'])
                continue


            # Check if user is in clan
            self.bot.cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toremove['ingame_name']))
            if not self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdDeletePlayer_error_notinclan'].format(name=player_toremove['ingame_name']))
                continue

            player_checked = True
        
        # Remove player from roster
        self.bot.cursor.execute("DELETE FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], player_toremove['ingame_name']))
        self.bot.conn.commit()
        await user.send(self.bot.quotes['cmdDeletePlayer_success'].format(name=player_toremove['ingame_name']))
        self.bot.async_loop.create_task(update.roster(self.bot))


        # Remove team role from player
        player_topm = discord.utils.get(self.guild.members, id=int(player_toremove['discord_id']))
        team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
        await player_topm.remove_roles(team_role)

        # Notify removed user
        await player_topm.send(self.bot.quotes['cmdDeletePlayer_success_dm'].format(teamname=team_toedit['name']))

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdDeletePlayer_log'].format(name=player_toremove['ingame_name'], teamname=team_toedit['name']))


    async def update_team_flag(self, team_toedit, user): # maybe with drop list?
        def check(m):
                return m.author == user and m.guild == None

        # Wait for team flag and check if this is a flag emoji 
        oldflag = flag.flagize(team_toedit['country'])
        country_checked = False
        while not country_checked:
            await user.send(self.bot.quotes['cmdUpdateFlag_prompt_flag'])
            country_msg = await self.bot.wait_for('message', check=check)
            country = country_msg.content.strip()
            serialized_country = flag.dflagize(country)

            # Cancel
            if country.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdUpdateFlag_cancel'])
                return

            self.bot.cursor.execute("SELECT id FROM Countries WHERE id = %s;", (serialized_country,))
            if not self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdRegister_error_country'])
            else:
                country_checked = True

        self.bot.cursor.execute("UPDATE Teams SET country=%s WHERE tag=%s", (serialized_country, team_toedit['tag']))
        self.bot.conn.commit()
        self.bot.async_loop.create_task(update.roster(self.bot))

        await user.send(self.bot.quotes['cmdUpdateFlag_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdUpdateFlag_log'].format(teamname=team_toedit['name'], oldflag=oldflag, newflag=country))

    async def change_clan_captain(self, team_toedit, user): # TODO: drop list 

        def check(m):
                return m.author == user and m.guild == None

        # Wait for the player auth, and check if it exist
        player_checked = False
        while not player_checked:
            await user.send(self.bot.quotes['cmdChangeCaptain_prompt_auth'])
            
            player_msg = await self.bot.wait_for('message', check=check)
            auth = player_msg.content.strip()

            # Cancel 
            if auth.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdChangeCaptain_cancel'])
                return

            # Check if the auth is registered
            self.bot.cursor.execute("SELECT ingame_name, discord_id FROM Users WHERE urt_auth = %s;", (auth,))
            new_captain = self.bot.cursor.fetchone()
            if not new_captain:
                await user.send(self.bot.quotes['cmdDeletePlayer_error_auth'].format(auth=auth))
                continue

            # Check if the user is trying to set captain to himself:
            if new_captain[1] == str(user.id):
                await user.send(self.bot.quotes['cmdChangeCaptain_error_alreadycap'])
                continue

            # Check if user is in clan
            self.bot.cursor.execute("SELECT id FROM Roster WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], new_captain['ingame_name']))
            if not self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdChangeCaptain_error_notinclan'].format(name=new_captain['ingame_name']))
                continue

            player_checked = True
        
        # Change clan captain
        self.bot.cursor.execute("UPDATE Roster SET accepted=2 WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], new_captain['ingame_name']))
        self.bot.conn.commit()

        self.bot.cursor.execute("UPDATE Teams SET captain=%s WHERE tag = %s ;", (new_captain['discord_id'], team_toedit['tag']))
        self.bot.conn.commit()

        # Remove captain status from prev captain
        prev_captain = discord.utils.get(self.guild.members, id=int(user.id))
        self.bot.cursor.execute("UPDATE Roster SET accepted=1 WHERE team_tag = %s AND player_name=%s;", (team_toedit['tag'], prev_captain.display_name))
        self.bot.conn.commit()

        self.bot.async_loop.create_task(update.roster(self.bot))
        await user.send(self.bot.quotes['cmdChangeCaptain_success'].format(name=new_captain['ingame_name']))

        # Notify new captain
        player_topm = discord.utils.get(self.bot.users, id=int(new_captain['discord_id']))
        await player_topm.send(self.bot.quotes['cmdChangeCaptain_success_dm'].format(teamname=team_toedit['name']))

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdChangeCaptain_log'].format(teamname=team_toedit['name'], oldcaptain=prev_captain.display_name, newcaptain=new_captain['ingame_name']))

    async def delete_team(self, team_toedit, user): # TODO: button
        def check(m):
                return m.author == user and m.guild == None 

        # Wait for the choice 
        await user.send(self.bot.quotes['cmdDeleteClan_intro'].format(teamname=team_toedit['name']))
        option_checked = False
        while not option_checked:
            await user.send(self.bot.quotes['cmdDeleteClan_prompt_choice'])
            choice_msg = await self.bot.wait_for('message', check=check)
            choice = choice_msg.content.lower().strip()

            # Cancel 
            if choice == '!cancel':
                await user.send(self.bot.quotes['cmdDeleteClan_prompt_cancel'])
                return

            # Cancel
            if choice == 'no':
                await user.send(self.bot.quotes['cmdDeleteClan_prompt_cancel'])
                return
            
            if choice == 'yes':
                # Remove roster message
                self.bot.cursor.execute("SELECT roster_message_id FROM Teams WHERE tag = %s;", (team_toedit['tag'],))
                roster_message_id = self.bot.cursor.fetchone()

                # Get channel and remove message
                roster_channel = discord.utils.get(self.guild.channels, id=self.bot.channel_roster_id)
                try:
                    roster_message = await roster_channel.fetch_message(roster_message_id['roster_message_id'])
                    await roster_message.delete()
                except:
                    pass

                # Delete team role
                try:
                    team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
                    await team_role.delete()
                except Exception as e:
                    print(e)

                # Delete clan
                self.bot.cursor.execute("DELETE FROM Teams WHERE tag = %s;", (team_toedit['tag'],))
                self.bot.conn.commit()

                # Delete from roster
                self.bot.cursor.execute("DELETE FROM Roster WHERE team_tag = %s;", (team_toedit['tag'],))
                self.bot.conn.commit()

                # Remove captain role if the captain is no longer captain of any team
                prev_captain = discord.utils.get(self.guild.members, id=int(user.id))
                captain_role = discord.utils.get(self.guild.roles, id=int(self.bot.role_captains_id))
                self.bot.cursor.execute("SELECT id FROM Roster WHERE accepted=2 AND player_name=%s", (prev_captain.display_name,))
                if not self.bot.cursor.fetchone():
                    await prev_captain.remove_roles(captain_role)

                # Notify
                await user.send(self.bot.quotes['cmdDeleteClan_prompt_success'].format(teamname=team_toedit['name']))

                # Print on the log channel
                log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                await log_channel.send(self.bot.quotes['cmdDeleteClan_log'].format(teamname=team_toedit['name']))

                # Update roster
                await update.roster(self.bot)

                return

def setup(bot):
    bot.add_cog(Clans(bot))