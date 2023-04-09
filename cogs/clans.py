import discord
from discord.ext import commands
from cogs.common.enums import RosterStatus
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check
import cogs.common.dropmenus as dropmenus
import flag

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component, interaction

from ftwgl import FTWClient, UserTeamRole


class Clans(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        user = discord.utils.get(self.guild.members, id=interaction.user.id)
        user_info = self.bot.db.get_player(discord_id=user.id)

        if interaction.component.id == "button_create_clan":
            # Check if the user already created 3 clans
            clans_created = self.bot.db.get_teams_of_player(user_info['id'])
            if len(clans_created) >= 3:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='You already created at least 3 clans, contact an admin if you want to delete one of them.')
                return

            # Check if user is busy
            if user.id in self.bot.users_busy:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdErrorBusy'])
                return


            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['CheckDm'])
            await self.createclan(user)

        elif interaction.component.id == "button_edit_clan":
            # List clans owned by the player
            clans = self.bot.db.get_teams_of_player(user_info['id'], admin_managed=0)

            # Not captain of any clan
            if not clans:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEditClan_error_notcaptain'])
                return

            # Get which clan to edit
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which clan do you want to edit?", components=dropmenus.teams(clans, None,  "dropmenu_teamtoedit"))

        elif interaction.component.id.startswith("button_edit_clan_"):
            # Get the clan to edit
            clan_tag = interaction.component.id.split("_")[-1]
            is_admin = interaction.component.id.split("_")[-2] == "admin"

            # just in case
            if is_admin and not user.guild_permissions.manage_guild:
                return

            clan_to_edit = self.bot.db.get_clan(tag=clan_tag)

            # Check if the clan is signed up for a cup ###################TEMPORARY############################
            # if self.bot.db.clan_in_active_cup(clan_to_edit['id']) and not is_admin:
            #     await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdEditClan_error_blocked_edit'])
            #     return

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

            if is_admin:
                # Get the ypdated team info
                clan_edited = self.bot.db.get_clan(tag=clan_tag)
                clan_embed, _ = embeds.team(self.bot, tag=clan_edited['tag'], show_invited=True)
                await interaction.message.edit(embed = clan_embed, components=self.get_editclan_buttons(clan_edited))

            # Update the roster
            self.bot.async_loop.create_task(update.roster(self.bot))
            self.bot.async_loop.create_task(update.signups(self.bot))

        elif interaction.component.id == "button_leave_clan":
            # List clans where the player is
            clans = self.bot.db.get_teams_player_member_inactive(user_info['id'])
            clan_infos = []
            for clan in clans:
                clan_infos.append(self.bot.db.get_clan(id=clan['team_id']))

            # Cant leave any clan 
            if not clans:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdLeaveClan_error_noclan'])
                return

            # Get which clan to leave
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Which clan do you want to leave?", components=dropmenus.teams(clan_infos, None,  "dropmenu_teamtoleave"))

        elif interaction.component.id.startswith("button_invite_"):
            # Get the clan to edit
            clan_id = interaction.component.id.split("_")[-1]
            team_toedit = self.bot.db.get_clan(id=clan_id)

            # Get captain info
            captain_info = self.bot.db.get_player(id=team_toedit['captain'])
            captain = discord.utils.get(self.guild.members, id=int(captain_info['discord_id']))

            # Disable invite buttons
            #print(interaction.message.id)
            #await interaction.message.edit(self.bot.quotes['cmdAddPlayer_invite'].format(captain=captain.display_name, teamname=team_toedit['name']), components=[[
            #                            Button(style=ButtonStyle.green, label="Accept", custom_id="button_invite_accept", disabled=True),
            #                            Button(style=ButtonStyle.red, label="Decline", custom_id="button_invite_decline", disabled=True),]])

            # Check if the player was still invited
            if not self.bot.db.get_roster_member(user_info['id'], team_toedit['id'], accepted=RosterStatus.Invited):
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddPlayer_nolongerinvited'].format(teamname=team_toedit['name']))
                return

            # Accepted invite
            if interaction.component.id.startswith("button_invite_accept"):
                self.bot.db.update_roster_status(RosterStatus.Member, user_info['id'], team_toedit['id'])
                ftw_client: FTWClient = self.bot.ftw
                await ftw_client.team_add_user_or_update_role(team_toedit['ftw_team_id'], user_info['discord_id'], UserTeamRole.member)

                await captain.send(self.bot.quotes['cmdAddPlayer_accepted_cap'].format(name=user_info['ingame_name'], teamname=team_toedit['name']))
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, ephemeral=False, content=self.bot.quotes['cmdAddPlayer_accepted'].format(teamname=team_toedit['name']))
                self.bot.async_loop.create_task(update.roster(self.bot))

                # Add team role to player
                team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
                await user.add_roles(team_role)

                # Print on the log channel
                log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                await log_channel.send(self.bot.quotes['cmdAddPlayer_accepted_log'].format(name=user_info['ingame_name'], teamname=team_toedit['name']))

            # Declined invite
            elif interaction.component.id.startswith("button_invite_decline"):
                await captain.send(self.bot.quotes['cmdAddPlayer_declined_cap'].format(name=user_info['ingame_name'], teamname=team_toedit['name']))
                self.bot.db.delete_player_from_roster(user_info['id'], team_id=team_toedit['id'])
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, ephemeral=False, content=self.bot.quotes['cmdAddPlayer_declined'].format(teamname=team_toedit['name']))

                # Print on the log channel
                log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                await log_channel.send(self.bot.quotes['cmdAddPlayer_declined_log'].format(name=user_info['ingame_name'], teamname=team_toedit['name']))


    @commands.Cog.listener() 
    async def on_select_option(self, interaction):
        #utils.ping_db(self.bot)
        
        if interaction.parent_component.id == "dropmenu_teamtoedit":
            user = discord.utils.get(self.guild.members, id=interaction.user.id)
            user_info = self.bot.db.get_player(discord_id=interaction.user.id)
            clans = self.bot.db.get_teams_of_player(user_info['id'], admin_managed=0)
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
            user_info = self.bot.db.get_player(discord_id=interaction.user.id)
            clans = self.bot.db.get_teams_player_member_inactive(user_info['id'])
            clan_to_leave = clans[int(interaction.component[0].value)]
            clan_info = self.bot.db.get_clan(id=clan_to_leave['team_id'])

            # Ask confirmation
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdLeaveClan_confirmation'].format(clanname=clan_info['name']), components=[[
                                        Button(style=ButtonStyle.green, label="Yes", custom_id="button_leaveclan_yes"),
                                        Button(style=ButtonStyle.red, label="No", custom_id="button_leaveclan_no"),]])
            interaction_leaveclanconfirmation = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_leaveclan_"))

            if interaction_leaveclanconfirmation.component.id == 'button_leaveclan_no':
                await interaction_leaveclanconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdLeaveClan_cancel'])
                return
            if interaction_leaveclanconfirmation.component.id == 'button_leaveclan_yes':
                self.bot.db.delete_player_from_roster(user_info['id'], clan_info['id'])

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



    async def createclan(self, user, admin_managed=0):
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
  
            if self.bot.db.get_clan(name=teamname):
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
 
            if self.bot.db.get_clan(tag=tag):
                await user.send(self.bot.quotes['cmdCreateClan_error_tag'])
            else:
                tag_checked = True

        # Wait for team flag and check if this is a flag emoji 
        country_checked = False
        while not country_checked:
            await user.send(self.bot.quotes['cmdCreateClan_prompt_flag'])
            country_msg = await self.bot.wait_for('message', check=check)
            country, country_checked = utils.check_flag_emoji(self.bot, country_msg.content.strip())

            # Cancel team creation
            if country_msg.content.strip().lower() == '!cancel':
                await user.send(self.bot.quotes['cmdCreateClan_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if not country_checked:
                await user.send(self.bot.quotes['cmdCreateClan_error_country'])

        # Create team ds role
        team_role = await self.guild.create_role(name=tag, mentionable=True)

        # Get captain info
        captain = self.bot.db.get_player(discord_id=user.id)

        # Add team to DB
        ftw_client: FTWClient = self.bot.ftw
        ftw_team_id = await ftw_client.team_create(user.id, teamname, tag)
        team_id = self.bot.db.create_clan(teamname, tag, country, captain['id'], team_role.id, ftw_team_id, admin_managed)

        # Add captain to team roster accepted=2 means captain
        captain_ds = discord.utils.get(self.guild.members, id=int(user.id))
        captain_role = discord.utils.get(self.guild.roles, id=int(self.bot.role_captains_id))
        await captain_ds.add_roles(captain_role, team_role)
        self.bot.db.create_roster_member(team_id, captain['id'], RosterStatus.Captain)

        ftw_client: FTWClient = self.bot.ftw
        await ftw_client.team_add_user_or_update_role(ftw_team_id, captain['discord_id'], UserTeamRole.leader)

        await user.send(self.bot.quotes['cmdCreateClan_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        embed, _ = embeds.team(self.bot, tag)
        await log_channel.send(content=self.bot.quotes['cmdCreateClan_log'], embed=embed)

        # Remove busy status
        self.bot.users_busy.remove(user.id)

        # Update roster
        self.bot.async_loop.create_task(update.post_roster(self.bot, admin_managed, team_id))

    async def add_player(self, team_toedit, user, interaction, is_admin=False):
        # Flag the user as busy
        self.bot.users_busy.append(user.id)

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
            # Remove busy status
            self.bot.users_busy.remove(user.id)
            return

        # Check if we are trying to add more players than the limit
        #if len(auth_list) + len(players_inclan) > self.bot.max_players_per_team:
        #    await user.send(self.bot.quotes['cmdAddPlayer_error_maxplayer'])
        #    return

        for auth in auth_list:
            auth = auth.strip()

            # Check if the auth is registered
            player_toadd = self.bot.db.get_player(urt_auth=auth)
            if not player_toadd:
                await user.send(self.bot.quotes['cmdAddPlayer_error_auth'].format(auth=auth))
                continue

            # Check if user was already invited
            if self.bot.db.get_roster_member(player_toadd['id'], team_toedit['id']):
                await user.send(self.bot.quotes['cmdAddPlayer_error_alreadyinvited'].format(name=player_toadd['ingame_name']))
                continue 

            # Check if the player is still on the discord
            player_topm = discord.utils.get(self.guild.members, id=int(player_toadd['discord_id']))
            if not player_topm:
                await user.send(self.bot.quotes['cmdAddPlayer_error_leftdiscord'].format(name=player_toadd['ingame_name']))
                continue

            # Add player to roster
            self.bot.db.create_roster_member(team_toedit['id'], player_toadd['id'], RosterStatus.Invited)
            ftw_client: FTWClient = self.bot.ftw
            await ftw_client.team_add_user_or_update_role(team_toedit['ftw_team_id'], player_toadd['discord_id'], UserTeamRole.invited)

            # Invite each player
            if not is_admin:
                await user.send(self.bot.quotes['cmdAddPlayer_invitesent'].format(name=player_toadd['ingame_name'])) 
                #self.bot.async_loop.create_task(self.invite_player(player_toadd, user, team_toedit))
                player_topm = discord.utils.get(self.guild.members, id=int(player_toadd['discord_id']))
                captain = discord.utils.get(self.guild.members, id=int(user.id)) 

                invite_msg = await player_topm.send(self.bot.quotes['cmdAddPlayer_invite'].format(captain=captain.display_name, teamname=team_toedit['name']), components=[[
                                            Button(style=ButtonStyle.green, label="Accept", custom_id=f"button_invite_accept_{team_toedit['id']}"),
                                            Button(style=ButtonStyle.red, label="Decline", custom_id=f"button_invite_decline_{team_toedit['id']}"),]])

                # Print on the log channel
                log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                await log_channel.send(self.bot.quotes['cmdAddPlayer_invite_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

            # If admin, force add
            else:
                player_topm = discord.utils.get(self.guild.members, id=int(player_toadd['discord_id']))
                self.bot.db.update_roster_status(RosterStatus.Member, player_toadd['id'], team_toedit['id'])

                ftw_client: FTWClient = self.bot.ftw
                await ftw_client.team_add_user_or_update_role(team_toedit['ftw_team_id'], player_toadd['discord_id'], UserTeamRole.member)

                await user.send(self.bot.quotes['cmdEditClan_admin_accepted_cap'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

                # Add team role to player
                team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
                await player_topm.add_roles(team_role)

                # Print on the log channel
                log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                await log_channel.send(self.bot.quotes['cmdEditClan_admin_addplayer_log'].format(name=player_toadd['ingame_name'], teamname=team_toedit['name']))

                # notify the player
                try:
                    await player_topm.send(self.bot.quotes['cmdAddPlayer_accepted'].format(teamname=team_toedit['name']))
                except:
                    print(f"Cant dm {player_toadd['urtauth']}.")


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
            self.bot.db.delete_player_from_roster(player_toremove['id'], team_toedit['id'])
            await interaction_removeplayerconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayer_success'].format(name=player_toremove['ingame_name']))

            # Remove team role from player
            player_topm = discord.utils.get(self.guild.members, id=int(player_toremove['discord_id']))
            if player_topm:
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
            self.bot.db.update_roster_status(RosterStatus.Inactive, player_addinactive['id'], team_toedit['id'])

            ftw_client: FTWClient = self.bot.ftw
            await ftw_client.team_add_user_or_update_role(team_toedit['ftw_team_id'], player_addinactive['discord_id'], UserTeamRole.inactive)

            await interaction_addinactiveconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdAddInactive_success'].format(name=player_addinactive['ingame_name']))

            # Remove team role from player
            player_topm = discord.utils.get(self.guild.members, id=int(player_addinactive['discord_id']))
            if player_topm:
                team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
                await player_topm.remove_roles(team_role)

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
            self.bot.db.update_roster_status(RosterStatus.Member, player_addinactive['id'], team_toedit['id'])

            ftw_client: FTWClient = self.bot.ftw
            await ftw_client.team_add_user_or_update_role(team_toedit['ftw_team_id'], player_addinactive['discord_id'], UserTeamRole.member)

            await interaction_removeinactiveconfirmation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdRemoveInactive_success'].format(name=player_addinactive['ingame_name']))

            # Add team role to player
            player_topm = discord.utils.get(self.guild.members, id=int(player_addinactive['discord_id']))
            if player_topm:
                team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
                await player_topm.add_roles(team_role)

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
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if not self.bot.db.get_country(id=serialized_country):
                await user.send(self.bot.quotes['cmdRegister_error_country'])
            else:
                country_checked = True

                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.db.edit_clan(team_toedit['tag'], country=serialized_country)
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

        self.bot.db.edit_clan(team_toedit['tag'], discord_link=link)
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

        # Check if the player is still on the discord
        player_topm = discord.utils.get(self.guild.members, id=int(new_captain['discord_id']))
        if not player_topm:
            await interaction_newcaptain.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdChangeCaptain_error_leftdiscord'].format(name=new_captain['ingame_name']))
            return


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
            self.bot.db.update_roster_status(RosterStatus.Captain, player_id=new_captain['id'], team_id=team_toedit['id'])
            ftw_client: FTWClient = self.bot.ftw
            await ftw_client.team_add_user_or_update_role(team_toedit['ftw_team_id'], new_captain['discord_id'], UserTeamRole.leader)
            self.bot.db.edit_clan(team_toedit['tag'], captain=new_captain['id'])

            # Get prev captain info
            prev_captain_info = self.bot.db.get_player(id=team_toedit['captain'])
            # Remove captain role if the captain is no longer captain of any team
            prev_captain = discord.utils.get(self.guild.members, id=int(prev_captain_info['discord_id']))
            self.bot.db.update_roster_status(RosterStatus.Member, player_id=team_toedit['captain'], team_id=team_toedit['id'])
            await ftw_client.team_add_user_or_update_role(team_toedit['ftw_team_id'], new_captain['discord_id'], UserTeamRole.member)

            # Remove captain discord role for previous captain if not captain of any clan
            captain_role = discord.utils.get(self.guild.roles, id=self.bot.role_captains_id)
            if not self.bot.db.get_teams_of_player(team_toedit['captain']):
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
            roster_message_id = self.bot.db.get_clan(tag=team_toedit['tag'])
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
            self.bot.db.delete_team(team_toedit['id'])

            # Get prev captain info
            prev_captain_info = self.bot.db.get_player(id=team_toedit['captain'])
            # Remove captain role if the captain is no longer captain of any team
            prev_captain = discord.utils.get(self.guild.members, id=int(prev_captain_info['discord_id']))
            if prev_captain:
                captain_role = discord.utils.get(self.guild.roles, id=int(self.bot.role_captains_id))
                if not self.bot.db.get_teams_of_player(team_toedit['captain']):
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
 
            if self.bot.db.get_clan(name=teamname):
                await user.send(self.bot.quotes['cmdCreateClan_error_name'])
            else:
                name_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.db.edit_clan(tag=team_toedit['tag'], name=teamname)
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

            if self.bot.db.get_clan(tag=tag):
                await user.send(self.bot.quotes['cmdCreateClan_error_tag'])
            else:
                tag_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.db.edit_clan(tag=team_toedit['tag'], newtag=tag)

        # Edit role name
        team_role = discord.utils.get(self.guild.roles, id=int(team_toedit['role_id']))
        await team_role.edit(name=tag)
        

        await user.send(self.bot.quotes['cmdUpdateTeamTag_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdUpdateTeamTag_log'].format(teamname=team_toedit['name'], oldtag=team_toedit['tag'], newtag=tag))


    def get_editclan_buttons(self, clan_to_edit):
        return [[
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
                ]]

    @commands.command() 
    @check.is_guild_manager()
    async def editclan(self, ctx, clan_toedit):
        # Check if user is busy
        if ctx.author.id in self.bot.users_busy:
            await ctx.send('You are currently busy with another action with the bot, finish it and try again')
            return

        # Get the team info
        clan_to_edit = self.bot.db.get_clan(tag=clan_toedit)

        if not clan_to_edit:
            await ctx.send(self.bot.quotes['cmdEditClan_admin_error_tag'])
            return

        # Get user's clan
        clan_embed, _ = embeds.team(self.bot, tag=clan_to_edit['tag'], show_invited=True)

        # Get the action to perform
        await ctx.send(embed = clan_embed, components=self.get_editclan_buttons(clan_to_edit))

    @commands.command() 
    @check.is_guild_manager()
    async def create_national_team(self, ctx):
        # Check if user is busy
        if ctx.author.id in self.bot.users_busy:
            await ctx.send('You are currently busy with another action with the bot, finish it and try again')
            return
        
        await self.createclan(ctx.author, 1)

        

def setup(bot):
    bot.add_cog(Clans(bot))