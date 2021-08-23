import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check
import cogs.common.dropmenus as dropmenus
import flag

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component, interaction

class Clans(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        user = discord.utils.get(self.guild.members, id=interaction.user.id)
        # Get user info
        self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id = %s;", (user.id,))
        user_info = self.bot.cursor.fetchone()

        if interaction.component.id == "button_create_clan":
            # Check if user is busy
            if user.id in self.bot.users_busy:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='You are currently busy with another action with the bot, finish it and click again')
                return

            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='Check your dms!')
            await self.createclan(user)

        if interaction.component.id == "button_edit_clan":
            # List clans owned by the player
            self.bot.cursor.execute("SELECT * FROM Teams WHERE captain = %s;", (user_info['id'],))
            clans = self.bot.cursor.fetchall()

            # Not captain of any clan
            if not clans:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEditClan_error_notcaptain'])
                return

            # Get which clan to edit
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which clan do you want to edit?", components=dropmenus.teams(clans, None,  "dropmenu_teamtoedit"))

        if interaction.component.id.startswith("button_edit_clan_"):
            # Get the clan to edit
            clan_tag = interaction.component.id.split("_")[-1]
            is_admin = interaction.component.id.split("_")[-2] == "admin"

            # just in case
            if is_admin and not user.guild_permissions.manage_guild:
                return

            self.bot.cursor.execute("SELECT * FROM Teams WHERE tag = %s;", (clan_tag,))
            clan_to_edit = self.bot.cursor.fetchone()

            # Launch the action
            if interaction.component.id.startswith("button_edit_clan_addplayer"):
                await self.add_player(clan_to_edit, user, interaction, is_admin)
            elif interaction.component.id.startswith("button_edit_clan_removeplayer"):
                await self.remove_player(clan_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_clan_changecaptain"):
                await self.change_clan_captain(clan_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_clan_addinactive"):
                await self.add_inactive(clan_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_clan_removeinactive"):
                await self.remove_inactive(clan_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_clan_changediscord"):
                await self.update_discord_link(clan_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_clan_changeflag"):
                await self.update_team_flag(clan_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_clan_deleteclan"):
                await self.delete_team(clan_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_clan_changename"):
                await self.update_team_name(clan_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_clan_changetag"):
                await self.update_team_tag(clan_to_edit, user, interaction)

            # Update the roster
            self.bot.async_loop.create_task(update.roster(self.bot))
            self.bot.async_loop.create_task(update.signups(self.bot))

        if interaction.component.id == "button_leave_clan":
            # List clans where the player is
            self.bot.cursor.execute("SELECT * FROM Roster WHERE player_id = %s AND (accepted=1 OR accepted=3);", (user_info['id'],))
            clans = self.bot.cursor.fetchall()
            clan_infos = []
            for clan in clans:
                self.bot.cursor.execute("SELECT * FROM Teams WHERE id = %s;", (clan['team_id'],))
                clan_infos.append(self.bot.cursor.fetchone())

            # Cant leave any clan 
            if not clans:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdLeaveClan_error_noclan'])
                return

            # Get which clan to leave
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which clan do you want to leave?", components=dropmenus.teams(clan_infos, None,  "dropmenu_teamtoleave"))

    @commands.Cog.listener() 
    async def on_select_option(self, interaction):
        #utils.ping_db(self.bot)
        
        if interaction.parent_component.id == "dropmenu_teamtoedit":
            user = discord.utils.get(self.guild.members, id=interaction.user.id)
            # Get user info
            self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id = %s;", (interaction.user.id,))
            user_info = self.bot.cursor.fetchone()

            # Get user's clan
            self.bot.cursor.execute("SELECT * FROM Teams WHERE captain = %s;", (user_info['id'],))
            clans = self.bot.cursor.fetchall()

            clan_to_edit = clans[int(interaction.component[0].value)]
            clan_embed, _ = embeds.team(self.bot, tag=clan_to_edit['tag'], show_invited=True)

            # Get the action to perform
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, embed = clan_embed, components=[[
                                    Button(style=ButtonStyle.green, label="Invite a player", custom_id=f"button_edit_clan_addplayer_{clan_to_edit['tag']}"),
                                    Button(style=ButtonStyle.blue, label="Remove a player", custom_id=f"button_edit_clan_removeplayer_{clan_to_edit['tag']}"),
                                    Button(style=ButtonStyle.blue, label="Change captain", custom_id=f"button_edit_clan_changecaptain_{clan_to_edit['tag']}"),
                                ],
                                [
                                    Button(style=ButtonStyle.grey, label="Add inactive", custom_id=f"button_edit_clan_addinactive_{clan_to_edit['tag']}"),
                                    Button(style=ButtonStyle.grey, label="Remove inactive", custom_id=f"button_edit_clan_removeinactive_{clan_to_edit['tag']}"),
                                ],
                                [
                                    Button(style=ButtonStyle.grey, label="Change discord", custom_id=f"button_edit_clan_changediscord_{clan_to_edit['tag']}"),
                                    Button(style=ButtonStyle.grey, label="Change flag", emoji = flag.flagize(clan_to_edit['country']), custom_id=f"button_edit_clan_changeflag_{clan_to_edit['tag']}"),
                                ],
                                [
                                    Button(style=ButtonStyle.grey, label="Change clan name", custom_id=f"button_edit_clan_changename_{clan_to_edit['tag']}"),
                                    Button(style=ButtonStyle.grey, label="Change tag", custom_id=f"button_edit_clan_changetag_{clan_to_edit['tag']}")
                                ]])

        if interaction.parent_component.id == "dropmenu_teamtoleave":
            user = discord.utils.get(self.guild.members, id=interaction.user.id)
            # Get user info
            self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id = %s;", (interaction.user.id,))
            user_info = self.bot.cursor.fetchone()

            # Get user's clan
            self.bot.cursor.execute("SELECT * FROM Roster WHERE player_id = %s AND (accepted=1 OR accepted=3);", (user_info['id'],))
            clans = self.bot.cursor.fetchall()
            clan_to_leave = clans[int(interaction.component[0].value)]

            # Get clan info
            self.bot.cursor.execute("SELECT * FROM Teams WHERE id = %s", (clan_to_leave['team_id'],))
            clan_info = self.bot.cursor.fetchone()

            # Ask confirmation
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdLeaveClan_confirmation'].format(clanname=clan_info['name']), components=[[
                                        Button(style=ButtonStyle.green, label="Yes", custom_id="button_leaveclan_yes"),
                                        Button(style=ButtonStyle.red, label="No", custom_id="button_leaveclan_no"),]])
            interaction_leaveclanconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_leaveclan_"))

            if interaction_leaveclanconfirmation.component.id == 'button_leaveclan_no':
                await interaction_leaveclanconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdLeaveClan_cancel'])
                return
            if interaction_leaveclanconfirmation.component.id == 'button_leaveclan_yes':
                #Leave the clan
                self.bot.cursor.execute("DELETE FROM Roster WHERE player_id=%s AND team_id=%s", (user_info['id'], clan_info['id']))
                self.bot.conn.commit()

                # Remove team role from player
                player_leaving = discord.utils.get(self.guild.members, id=int(user_info['discord_id']))
                team_role = discord.utils.get(self.guild.roles, id=int(clan_info['role_id']))
                await player_leaving.remove_roles(team_role)

                # Notify
                await interaction_leaveclanconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdLeaveClan_success'].format(clanname=clan_info['name']))

                # Print on the log channel
                log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                await log_channel.send(content=self.bot.quotes['cmdLeaveClan_log'].format(playername = user_info['ingame_name'], teamname=clan_info['name']))

                # Update the roster
                self.bot.async_loop.create_task(update.roster(self.bot))



    async def createclan(self, user):
        # Flag the user as busy
        self.bot.users_busy.append(user.id)

        def check(m):
                return m.author == user and m.guild == None

        await user.send(self.bot.quotes['cmdCreateClan_intro'])

        # Wait for team name and check if the clan name is taken
        name_checked = False
        while not name_checked:
            await user.send(self.bot.quotes['cmdCreateClan_prompt_name'])
            teamname_msg = await self.bot.wait_for('message', check=check)
            teamname = teamname_msg.content.strip()

            # Cancel team creation
            if teamname.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdCreateClan_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if utils.emojis_in(teamname_msg.content.strip()) or len(teamname_msg.content.strip()) > 50:
                await user.send("Invalid entry, too long or includes emoji, try again.")
                continue

            self.bot.cursor.execute("SELECT id FROM Teams WHERE name = %s", (teamname,))   
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdCreateClan_error_name'])
            else:
                name_checked = True


        # Wait for team tag and check if the team tag is taken    
        tag_checked = False
        while not tag_checked:
            await user.send(self.bot.quotes['cmdCreateClan_prompt_tag'])
            tag_msg = await self.bot.wait_for('message', check=check)
            tag = tag_msg.content.strip()

            # Cancel team creation
            if tag.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdCreateClan_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if utils.emojis_in(tag_msg.content.strip()) or len(tag_msg.content.strip()) > 50:
                await user.send("Invalid entry, too long or includes emoji, try again.")
                continue

            self.bot.cursor.execute("SELECT id FROM Teams WHERE tag = %s", (tag,))   
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdCreateClan_error_tag'])
            else:
                tag_checked = True

        # Wait for team flag and check if this is a flag emoji 
        country_checked = False
        while not country_checked:
            await user.send(self.bot.quotes['cmdCreateClan_prompt_flag'])
            country_msg = await self.bot.wait_for('message', check=check)
            country, country_checked = utils.check_flag_emoji(self.bot.cursor, country_msg.content.strip())

            # Cancel team creation
            if country_msg.content.strip().lower() == '!cancel':
                await user.send(self.bot.quotes['cmdCreateClan_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if not country_checked:
                await user.send(self.bot.quotes['cmdCreateClan_error_country'])

        # Create team ds role
        team_role = await self.guild.create_role(name=tag)

        # Get captain info
        self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id=%s", (user.id,))
        captain = self.bot.cursor.fetchone()

        # Add team to DB
        self.bot.cursor.execute("INSERT INTO Teams(name, tag, country, captain, role_id) VALUES (%s, %s, %s, %s, %s) ;", (teamname, tag, country, captain['id'], team_role.id))
        self.bot.conn.commit()
        team_id = self.bot.cursor.lastrowid

        # Add captain to team roster accepted=2 means captain
        captain_ds = discord.utils.get(self.guild.members, id=int(user.id))
        captain_role = discord.utils.get(self.guild.roles, id=int(self.bot.role_captains_id))
        await captain_ds.add_roles(captain_role, team_role)
        self.bot.cursor.execute("INSERT INTO Roster(team_id, player_id, accepted) VALUES (%s, %s, %d) ;", (team_id, captain['id'], 2))
        self.bot.conn.commit()

        await user.send(self.bot.quotes['cmdCreateClan_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        embed, _ = embeds.team(self.bot, tag)
        await log_channel.send(content=self.bot.quotes['cmdCreateClan_log'], embed=embed)

        # Remove busy status
        self.bot.users_busy.remove(user.id)

        # Update roster
        self.bot.async_loop.create_task(update.roster(self.bot))

    async def add_player(self, team_toedit, user, interaction, is_admin=False):
        # Flag the user as busy
        self.bot.users_busy.append(user.id)
        
        # Check if the max number of players per clan has been reached
        self.bot.cursor.execute("SELECT * FROM Roster WHERE team_id = %s;", (team_toedit['id'],))
        players_inclan = self.bot.cursor.fetchall()
        if len(players_inclan) >= self.bot.max_players_per_team:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddPlayer_error_maxplayer'])
            return

        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Check your dms!")

        def check(m):
                return m.author == user and m.guild == None

        # Wait for the auth list to add
        await user.send(self.bot.quotes['cmdAddPlayer_prompt_auth'])
        
        player_msg = await self.bot.wait_for('message', check=check)
        auth_list = player_msg.content.strip().split(',')

        # Remove busy status
        self.bot.users_busy.remove(user.id)

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
            self.bot.cursor.execute("SELECT * FROM Users WHERE urt_auth = %s;", (auth,))
            player_toadd = self.bot.cursor.fetchone()
            if not player_toadd:
                await user.send(self.bot.quotes['cmdAddPlayer_error_auth'].format(auth=auth))
                continue

            # Check if user was already invited
            self.bot.cursor.execute("SELECT * FROM Roster WHERE team_id = %s AND player_id=%s;", (team_toedit['id'], player_toadd['id']))
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdAddPlayer_error_alreadyinvited'].format(name=player_toadd['ingame_name']))
                continue 

            # Add player to roster
            self.bot.cursor.execute("INSERT INTO Roster(team_id, player_id) VALUES (%s, %s) ;", (team_toedit['id'], player_toadd['id']))
            self.bot.conn.commit() 

            # Invite each player
            if not is_admin:
                await user.send(self.bot.quotes['cmdAddPlayer_invitesent'].format(name=player_toadd['ingame_name'])) 
                self.bot.async_loop.create_task(self.invite_player(player_toadd, user, team_toedit))

            # If admin, force add
            else:
                player_topm = discord.utils.get(self.guild.members, id=int(player_toadd['discord_id']))
                self.bot.cursor.execute("UPDATE Roster SET accepted=1 WHERE  team_id = %s AND player_id=%s;", (team_toedit['id'], player_toadd['id']))
                self.bot.conn.commit()

                await user.send(self.bot.quotes['cmdEditClan_admin_accepted_cap'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

                # Add team role to player
                team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
                await player_topm.add_roles(team_role)

                # Print on the log channel
                log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                await log_channel.send(self.bot.quotes['cmdEditClan_admin_addplayer_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

                # notify the player
                await player_topm.send(self.bot.quotes['cmdAddPlayer_accepted'].format(teamname=team_toedit['name']))

    async def invite_player(self, player_toadd, user, team_toedit):
        # DM invite to user
        player_topm = discord.utils.get(self.guild.members, id=int(player_toadd['discord_id']))
        captain = discord.utils.get(self.guild.members, id=int(user.id)) 

        invite_message = await player_topm.send(self.bot.quotes['cmdAddPlayer_invite'].format(captain=captain.display_name, teamname=team_toedit['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Accept", custom_id="button_invite_accept"),
                                    Button(style=ButtonStyle.red, label="Decline", custom_id="button_invite_decline"),]])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdAddPlayer_invite_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

        # Wait for button press 
        interaction_inviteresponse = await self.bot.wait_for("button_click", check = lambda i: i.user.id == player_topm.id and i.component.id.startswith("button_invite_"))

        # Disable invite buttons
        await invite_message.edit(self.bot.quotes['cmdAddPlayer_invite'].format(captain=captain.display_name, teamname=team_toedit['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Accept", custom_id="button_invite_accept", disabled=True),
                                    Button(style=ButtonStyle.red, label="Decline", custom_id="button_invite_decline", disabled=True),]])

        # Check if the player was still invited
        self.bot.cursor.execute("SELECT id FROM Roster WHERE accepted=0 AND team_id = %s AND player_id=%s;", (team_toedit['id'], player_toadd['id']))
        if not self.bot.cursor.fetchone():
            await player_topm.send(self.bot.quotes['cmdAddPlayer_nolongerinvited'].format(teamname=team_toedit['name']))
            return

        # Accepted invite
        if interaction_inviteresponse.component.id == "button_invite_accept":
            self.bot.cursor.execute("UPDATE Roster SET accepted=1 WHERE  team_id = %s AND player_id=%s;", (team_toedit['id'], player_toadd['id']))
            self.bot.conn.commit()

            await captain.send(self.bot.quotes['cmdAddPlayer_accepted_cap'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))
            await interaction_inviteresponse.respond(type=InteractionType.ChannelMessageWithSource, ephemeral=False, content=self.bot.quotes['cmdAddPlayer_accepted'].format(teamname=team_toedit['name']))
            self.bot.async_loop.create_task(update.roster(self.bot))

            # Add team role to player
            team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
            await player_topm.add_roles(team_role)

            # Print on the log channel
            await log_channel.send(self.bot.quotes['cmdAddPlayer_accepted_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

        # Declined invite
        elif interaction_inviteresponse.component.id == "button_invite_decline":
            await captain.send(self.bot.quotes['cmdAddPlayer_declined_cap'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))
            self.bot.cursor.execute("DELETE FROM Roster WHERE  team_id = %s AND player_id=%s;", (team_toedit['id'], player_toadd['id']))
            self.bot.conn.commit()
            await interaction_inviteresponse.respond(type=InteractionType.ChannelMessageWithSource, ephemeral=False, content=self.bot.quotes['cmdAddPlayer_declined'].format(teamname=team_toedit['name']))

            # Print on the log channel
            await log_channel.send(self.bot.quotes['cmdAddPlayer_declined_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))


    async def remove_player(self, team_toedit, user, interaction):

        # Get which player to remove
        player_info_list, dropmenu_playertoremove = dropmenus.players_of_team(self.bot, team_toedit['id'], "dropmenu_player_to_remove", include_invited=True, include_inactive=True)
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which player do you want to remove from your clan?", components=dropmenu_playertoremove)
        interaction_removeplayer = await self.bot.wait_for("select_option", check = lambda i: i.user.id == user.id and i.parent_component.id == "dropmenu_player_to_remove")
        player_toremove = player_info_list[int(interaction_removeplayer.component[0].value)]

        # Ask confirmation
        await interaction_removeplayer.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayer_confirmation'].format(name=player_toremove['ingame_name'], teamname=team_toedit['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_removeplayer_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_removeplayer_no"),]])
        interaction_removeplayerconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_removeplayer_"))

        if interaction_removeplayerconfirmation.component.id == 'button_removeplayer_no':
            await interaction_removeplayerconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayer_cancel'])
            return
        
        if interaction_removeplayerconfirmation.component.id == 'button_removeplayer_yes':
            # Remove player from roster
            self.bot.cursor.execute("DELETE FROM Roster WHERE team_id = %s AND player_id=%s;", (team_toedit['id'], player_toremove['id']))
            self.bot.conn.commit()

            await interaction_removeplayerconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayer_success'].format(name=player_toremove['ingame_name']))

            # Remove team role from player
            player_topm = discord.utils.get(self.guild.members, id=int(player_toremove['discord_id']))
            team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
            await player_topm.remove_roles(team_role)

            # Notify removed user
            await player_topm.send(self.bot.quotes['cmdDeletePlayer_success_dm'].format(teamname=team_toedit['name']))

            # Print on the log channel
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdDeletePlayer_log'].format(name=player_toremove['ingame_name'], teamname=team_toedit['name']))

    async def add_inactive(self, team_toedit, user, interaction):

        # Get which player to add as inactive
        player_info_list, dropmenu_playertoaddinactive = dropmenus.players_of_team(self.bot, team_toedit['id'], "dropmenu_player_to_add_inactive")

        # Check if there are no player to set as inactive
        if len(player_info_list) == 0:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="No player to set as inactive")
            return


        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which player do you want to set as inactive?", components=dropmenu_playertoaddinactive)
        interaction_addinactive = await self.bot.wait_for("select_option", check = lambda i: i.user.id == user.id and i.parent_component.id == "dropmenu_player_to_add_inactive")
        player_addinactive = player_info_list[int(interaction_addinactive.component[0].value)]

        # Ask confirmation
        await interaction_addinactive.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddInactive_confirmation'].format(name=player_addinactive['ingame_name'], teamname=team_toedit['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_addinactive_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_addinactive_no"),]])
        interaction_addinactiveconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_addinactive_"))

        if interaction_addinactiveconfirmation.component.id == 'button_addinactive_no':
            await interaction_addinactiveconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddInactive_cancel'])
            return
        
        if interaction_addinactiveconfirmation.component.id == 'button_addinactive_yes':
            # Set as inactive
            self.bot.cursor.execute("UPDATE Roster SET accepted = 3 WHERE team_id = %s AND player_id=%s;", (team_toedit['id'], player_addinactive['id']))
            self.bot.conn.commit()

            await interaction_addinactiveconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddInactive_success'].format(name=player_addinactive['ingame_name']))

            # Print on the log channel
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdAddInactive_log'].format(name=player_addinactive['ingame_name'], teamname=team_toedit['name']))

    async def remove_inactive(self, team_toedit, user, interaction):

        # Get which player to remove as inactive
        player_info_list, dropmenu_playertoremoveinactive = dropmenus.players_of_team(self.bot, team_toedit['id'], "dropmenu_player_to_remove_inactive", include_members=False, include_inactive=True)
        
        # Check if there are no player to set as inactive
        if len(player_info_list) == 0:
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="No player to remove from inactives")
            return


        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which player do you want to remove from inactives?", components=dropmenu_playertoremoveinactive)
        interaction_removeinactive = await self.bot.wait_for("select_option", check = lambda i: i.user.id == user.id and i.parent_component.id == "dropmenu_player_to_remove_inactive")
        player_addinactive = player_info_list[int(interaction_removeinactive.component[0].value)]

        # Ask confirmation
        await interaction_removeinactive.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdRemoveInactive_confirmation'].format(name=player_addinactive['ingame_name'], teamname=team_toedit['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_removeinactive_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_removeinactive_no"),]])
        interaction_removeinactiveconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_removeinactive_"))

        if interaction_removeinactiveconfirmation.component.id == 'button_removeinactive_no':
            await interaction_removeinactiveconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdRemoveInactive_cancel'])
            return
        
        if interaction_removeinactiveconfirmation.component.id == 'button_removeinactive_yes':
            # Remove as inactive
            self.bot.cursor.execute("UPDATE Roster SET accepted = 1 WHERE team_id = %s AND player_id=%s;", (team_toedit['id'], player_addinactive['id']))
            self.bot.conn.commit()

            await interaction_removeinactiveconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdRemoveInactive_success'].format(name=player_addinactive['ingame_name']))

            # Print on the log channel
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdRemoveInactive_log'].format(name=player_addinactive['ingame_name'], teamname=team_toedit['name']))


    async def update_team_flag(self, team_toedit, user, interaction): 
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Check your dms!")

        # Flag the user as busy
        self.bot.users_busy.append(user.id)

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

                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.cursor.execute("UPDATE Teams SET country=%s WHERE tag=%s", (serialized_country, team_toedit['tag']))
        self.bot.conn.commit()

        await user.send(self.bot.quotes['cmdUpdateFlag_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdUpdateFlag_log'].format(teamname=team_toedit['name'], oldflag=oldflag, newflag=country))

    async def update_discord_link(self, team_toedit, user, interaction): # maybe with drop list?
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Check your dms!")

        # Flag the user as busy
        self.bot.users_busy.append(user.id)
        
        def check(m):
                return m.author == user and m.guild == None

        # Wait for discord link  
        link_checked = False
        while not link_checked:
            await user.send(self.bot.quotes['cmdUpdateDiscordLink_prompt_link'])
            link_msg = await self.bot.wait_for('message', check=check)
            link = link_msg.content.strip()

            # Cancel
            if link.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdUpdateDiscordLink_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if "discord.gg/" not in link:
                await user.send(self.bot.quotes['cmdUpdateDiscordLink_error_link'])
            else:
                link_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.cursor.execute("UPDATE Teams SET discord_link=%s WHERE tag=%s", (link, team_toedit['tag']))
        self.bot.conn.commit()

        await user.send(self.bot.quotes['cmdUpdateDiscordLink_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdUpdateDiscordLink_log'].format(teamname=team_toedit['name'], newlink=link))

    async def change_clan_captain(self, team_toedit, user, interaction): 
        # Get which player for new cap
        player_info_list, dropmenu_newcap = dropmenus.players_of_team(self.bot, team_toedit['id'], "dropmenu_player_newcaptain", include_inactive=True)
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdChangeCaptain_prompt_auth'], components=dropmenu_newcap)
        interaction_newcaptain = await self.bot.wait_for("select_option", check = lambda i: i.user.id == user.id and i.parent_component.id == "dropmenu_player_newcaptain")
        new_captain = player_info_list[int(interaction_newcaptain.component[0].value)]

        # Ask confirmation
        await interaction_newcaptain.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdChangeCaptain_confirmation'].format(name=new_captain['ingame_name'], teamname=team_toedit['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_changecaptain_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_changecaptain_no"),]])
        interaction_changecaptainconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_changecaptain_"))

        if interaction_changecaptainconfirmation.component.id == 'button_changecaptain_no':
            await interaction_changecaptainconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdChangeCaptain_cancel'])
            return
        
        if interaction_changecaptainconfirmation.component.id == 'button_changecaptain_yes':
            # Change clan captain
            self.bot.cursor.execute("UPDATE Roster SET accepted=2 WHERE team_id = %s AND player_id=%s;", (team_toedit['id'], new_captain['id']))
            self.bot.conn.commit()

            self.bot.cursor.execute("UPDATE Teams SET captain=%s WHERE tag = %s ;", (new_captain['id'], team_toedit['tag']))
            self.bot.conn.commit()

            # Get prev captain info
            self.bot.cursor.execute("SELECT * FROM Users WHERE id=%s", (team_toedit['captain'],))
            prev_captain_info = self.bot.cursor.fetchone()
            # Remove captain role if the captain is no longer captain of any team
            prev_captain = discord.utils.get(self.guild.members, id=int(prev_captain_info['discord_id']))
            self.bot.cursor.execute("UPDATE Roster SET accepted=1 WHERE team_id = %s AND player_id=%s;", (team_toedit['id'], team_toedit['captain']))
            self.bot.conn.commit()

            # Remove captain discord role for previous captain if not captain of any clan
            captain_role = discord.utils.get(self.guild.roles, id=self.bot.role_captains_id)
            self.bot.cursor.execute("SELECT * FROM Roster WHERE accepted=2 AND player_id=%s;", (team_toedit['captain'],))
            if not self.bot.cursor.fetchone():
                await prev_captain.remove_roles(captain_role)

            await interaction_changecaptainconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdChangeCaptain_success'].format(name=new_captain['ingame_name']))

            # Notify new captain
            player_topm = discord.utils.get(self.guild.members, id=int(new_captain['discord_id']))
            await player_topm.send(self.bot.quotes['cmdChangeCaptain_success_dm'].format(teamname=team_toedit['name']))
            await player_topm.add_roles(captain_role)

            # Print on the log channel
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdChangeCaptain_log'].format(teamname=team_toedit['name'], oldcaptain=prev_captain.display_name, newcaptain=new_captain['ingame_name']))

    async def delete_team(self, team_toedit, user, interaction):
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeleteClan_intro'].format(teamname=team_toedit['name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_deleteclan_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_deleteclan_no"),]])
        interaction_deleteclan = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_deleteclan_"))

        if interaction_deleteclan.component.id == 'button_deleteclan_no':
            await interaction_deleteclan.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeleteClan_prompt_cancel'])
            return
        
        if interaction_deleteclan.component.id == 'button_deleteclan_yes':
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
            self.bot.cursor.execute("DELETE FROM Roster WHERE team_id = %s;", (team_toedit['id'],))
            self.bot.conn.commit()

            # Delete from signups
            self.bot.cursor.execute("DELETE FROM Signups WHERE team_id = %s;", (team_toedit['id'],))
            self.bot.conn.commit()

            

            # Get prev captain info
            self.bot.cursor.execute("SELECT * FROM Users WHERE id=%s", (team_toedit['captain'],))
            prev_captain_info = self.bot.cursor.fetchone()
            # Remove captain role if the captain is no longer captain of any team
            prev_captain = discord.utils.get(self.guild.members, id=int(prev_captain_info['discord_id']))
            captain_role = discord.utils.get(self.guild.roles, id=int(self.bot.role_captains_id))
            self.bot.cursor.execute("SELECT id FROM Roster WHERE accepted=2 AND player_id=%s", (prev_captain_info['id'],))
            if not self.bot.cursor.fetchone():
                await prev_captain.remove_roles(captain_role)

            # Notify
            await interaction_deleteclan.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeleteClan_prompt_success'].format(teamname=team_toedit['name']))

            # Print on the log channel
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdDeleteClan_log'].format(teamname=team_toedit['name']))

    async def update_team_name(self, team_toedit, user, interaction): 
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Check your dms!")

        # Flag the user as busy
        self.bot.users_busy.append(user.id)

        def check(m):
                return m.author == user and m.guild == None

        # Wait for team name and check if the clan name is taken
        name_checked = False
        while not name_checked:
            await user.send(self.bot.quotes['cmdCreateClan_prompt_name'])
            teamname_msg = await self.bot.wait_for('message', check=check)
            teamname = teamname_msg.content.strip()

            # Cancel team edition
            if teamname.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdEditClan_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if utils.emojis_in(teamname_msg.content.strip()) or len(teamname_msg.content.strip()) > 50:
                await user.send("Invalid entry, too long or includes emoji, try again.")
                continue

            self.bot.cursor.execute("SELECT id FROM Teams WHERE name = %s", (teamname,))   
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdCreateClan_error_name'])
            else:
                name_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.cursor.execute("UPDATE Teams SET name=%s WHERE tag=%s", (teamname, team_toedit['tag']))
        self.bot.conn.commit()

        await user.send(self.bot.quotes['cmdUpdateTeamName_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdUpdateTeamName_log'].format(oldname=team_toedit['name'], newname=teamname))

    async def update_team_tag(self, team_toedit, user, interaction): 
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Check your dms!")

        # Flag the user as busy
        self.bot.users_busy.append(user.id)

        def check(m):
                return m.author == user and m.guild == None

        # Wait for team tag and check if the team tag is taken    
        tag_checked = False
        while not tag_checked:
            await user.send(self.bot.quotes['cmdCreateClan_prompt_tag'])
            tag_msg = await self.bot.wait_for('message', check=check)
            tag = tag_msg.content.strip()

            # Cancel team creation
            if tag.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdEditClan_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if utils.emojis_in(tag_msg.content.strip()) or len(tag_msg.content.strip()) > 50:
                await user.send("Invalid entry, too long or includes emoji, try again.")
                continue

            self.bot.cursor.execute("SELECT id FROM Teams WHERE tag = %s", (tag,))   
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdCreateClan_error_tag'])
            else:
                tag_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.cursor.execute("UPDATE Teams SET tag=%s WHERE tag=%s", (tag, team_toedit['tag']))
        self.bot.conn.commit()

        await user.send(self.bot.quotes['cmdUpdateTeamTag_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdUpdateTeamTag_log'].format(teamname=team_toedit['name'], oldtag=team_toedit['tag'], newtag=tag))

    @commands.command() 
    @check.is_guild_manager()
    async def editclan(self, ctx, clan_toedit):
        # Check if user is busy
        if ctx.author.id in self.bot.users_busy:
            await ctx.send('You are currently busy with another action with the bot, finish it and try again')
            return

        # Get the team info
        self.bot.cursor.execute("SELECT * FROM Teams WHERE tag=%s;", (clan_toedit,))
        clan_to_edit = self.bot.cursor.fetchone()

        if not clan_to_edit:
            await ctx.send(self.bot.quotes['cmdEditClan_admin_error_tag'])
            return

        # Get user's clan
        clan_embed, _ = embeds.team(self.bot, tag=clan_to_edit['tag'], show_invited=True)

        # Get the action to perform
        await ctx.send(embed = clan_embed, components=[[
                                Button(style=ButtonStyle.green, label="Add a player", custom_id=f"button_edit_clan_addplayer_admin_{clan_to_edit['tag']}"),
                                Button(style=ButtonStyle.blue, label="Remove a player", custom_id=f"button_edit_clan_removeplayer_admin_{clan_to_edit['tag']}"),
                                Button(style=ButtonStyle.blue, label="Change captain", custom_id=f"button_edit_clan_changecaptain_admin_{clan_to_edit['tag']}"),
                            ],
                            [
                                Button(style=ButtonStyle.grey, label="Add inactive", custom_id=f"button_edit_clan_addinactive_admin_{clan_to_edit['tag']}"),
                                Button(style=ButtonStyle.grey, label="Remove inactive", custom_id=f"button_edit_clan_removeinactive_admin_{clan_to_edit['tag']}"),
                            ],
                            [
                                Button(style=ButtonStyle.grey, label="Change discord", custom_id=f"button_edit_clan_changediscord_admin_{clan_to_edit['tag']}"),
                                Button(style=ButtonStyle.grey, label="Change flag", emoji = flag.flagize(clan_to_edit['country']), custom_id=f"button_edit_clan_changeflag_admin_{clan_to_edit['tag']}")
                            ],
                            [
                                Button(style=ButtonStyle.grey, label="Change clan name", custom_id=f"button_edit_clan_changename_admin_{clan_to_edit['tag']}"),
                                Button(style=ButtonStyle.grey, label="Change tag", custom_id=f"button_edit_clan_changetag_admin_{clan_to_edit['tag']}")
                            ],
                            [
                                Button(style=ButtonStyle.red, label="Delete clan", custom_id=f"button_edit_clan_deleteclan_admin_{clan_to_edit['tag']}")
                            ]])

        

def setup(bot):
    bot.add_cog(Clans(bot))