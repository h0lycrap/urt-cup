import discord
from discord.ext import commands
from cogs.common.enums import RosterStatus
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.check as check
import cogs.common.update as update
import flag

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

from ftwgl import FTWClient, UserTeamRole


class Account(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_message(self, message):
        #utils.ping_db(self.bot)
        pass

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        #utils.ping_db(self.bot)
        user = discord.utils.get(self.guild.members, id=interaction.user.id)

        if interaction.component.id == "button_register":
            # Check if user is already registered
            if self.bot.db.get_player(discord_id=interaction.user.id):
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='User already registered')
                return
            
            # Check if user is busy
            if user.id in self.bot.users_busy:
                await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='You are already in the registration process, finish it in your dms')
                return
            
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content='Check your dms!')
            await self.register(user)

        if interaction.component.id.startswith("button_edit_player_"):
            # Get the clan to edit
            player_id = interaction.component.id.split("_")[-1]
            is_admin = interaction.component.id.split("_")[-2] == "admin"

            # just in case
            if is_admin and not user.guild_permissions.manage_guild:
                return

            player_to_edit = self.bot.db.get_player(id=player_id)

            # Launch the action
            if interaction.component.id.startswith("button_edit_player_changename"):
                await self.update_player_name(player_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_player_changeauth"):
                await self.update_player_auth(player_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_player_changeflag"):
                await self.update_player_flag(player_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_player_delete"):
                await self.delete_player(player_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_player_verify_country"):
                await self.verify_country(player_to_edit, user, interaction)

            if is_admin:
                # Get the updated player info
                player_edited = self.bot.db.get_player(id=player_id)
                player_embed = embeds.player(self.bot, auth=player_edited['urt_auth'])
                editplayer_buttons = self.get_editplayer_buttons(player_edited)
                await interaction.message.edit(embed = player_embed, components=editplayer_buttons)

            # Update the roster
            self.bot.async_loop.create_task(update.roster(self.bot))

    
    @commands.command() 
    @check.is_guild_manager()
    async def forceregister(self, ctx, discord_id, auth, name, flag):   
        # Check discord id
        user = discord.utils.get(self.guild.members, id=int(discord_id))
        if not user:
            await ctx.send("Discord id not on server")
            return

        # Check if auth is already registered
        if self.bot.db.get_player(urt_auth=auth):
            await ctx.send(self.bot.quotes['cmdRegister_error_authalreadyreg'])
            return

        if not utils.check_auth(auth):
            await ctx.send(self.bot.quotes['cmdRegister_error_authdoesntexist'])
            return

        # Check if ingame name is already taken 
        if self.bot.db.get_player(ingame_name=name):
            await ctx.send(self.bot.quotes['cmdRegister_error_nametaken'])
            return

        country, country_checked = utils.check_flag_emoji(self.bot, flag)

        if not country_checked:
            await ctx.send(self.bot.quotes['cmdRegister_error_country'])
            return

        # Add user to DB and remove unregistered role
        self.bot.db.create_player(user.id, auth, name, country)
        ftw_client: FTWClient = self.bot.ftw
        await ftw_client.user_create_or_update(user.id, auth, name)
        await ctx.send(self.bot.quotes['cmdRegister_success'])
        await user.remove_roles(discord.utils.get(self.guild.roles, id=self.bot.role_unregistered_id))

        # Remove busy status
        try:
            self.bot.users_busy.remove(user.id)
        except:
            pass

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        embed = embeds.player(self.bot, auth)
        await log_channel.send(content=self.bot.quotes['cmdRegister_log'], embed=embed)

        # There can be permission errors if the user's role is higher in hierarchy than the bot
        try:
            await user.edit(nick=name)
        except Exception as e:
            pass

    
    async def register(self, user):
        #flag user as busy
        self.bot.users_busy.append(user.id)

        def check(m):
                return m.author.id == user.id and m.guild == None

        await user.send(self.bot.quotes['cmdRegister_intro'])

        # Wait for team name and check if the team name is taken
        auth_checked = False
        while not auth_checked:
            await user.send(self.bot.quotes['cmdRegister_prompt_auth'])
            auth_msg = await self.bot.wait_for('message', check=check)
            auth = auth_msg.content.strip()

            # Check if auth is already registered 
            if self.bot.db.get_player(urt_auth=auth):
                await user.send(self.bot.quotes['cmdRegister_error_authalreadyreg'])
                continue
            
            if not auth.isalnum():
                await user.send(self.bot.quotes['cmdRegister_error_invalidauth'])
                continue

            if not utils.check_auth(auth):
                await user.send(self.bot.quotes['cmdRegister_error_authdoesntexist'])
                continue

            auth_checked = True

        name_checked = False
        while not name_checked:
            await user.send(self.bot.quotes['cmdRegister_prompt_name'])
            name_msg = await self.bot.wait_for('message', check=check)
            name = name_msg.content.strip()

            if utils.emojis_in(name_msg.content.strip()) or len(name_msg.content.strip()) > 50:
                await user.send("Invalid entry, too long or includes emoji, try again.")
                continue

            # Check if ingame name is already taken
            if self.bot.db.get_player(ingame_name=name):
                await user.send(self.bot.quotes['cmdRegister_error_nametaken'])
            else:
                name_checked = True

        # Wait for flag and check if this is a flag emoji 
        country_checked = False
        while not country_checked:
            await user.send(self.bot.quotes['cmdRegister_prompt_country'])
            country_msg = await self.bot.wait_for('message', check=check)
            country, country_checked = utils.check_flag_emoji(self.bot, country_msg.content.strip())

            if not country_checked:
                await user.send(self.bot.quotes['cmdRegister_error_country'])

        # Add user to DB and remove unregistered role
        self.bot.db.create_player(user.id, auth, name, country)
        ftw_client: FTWClient = self.bot.ftw
        await ftw_client.user_create_or_update(user.id, auth, name)

        await user.send(self.bot.quotes['cmdRegister_success'])
        await user.remove_roles(discord.utils.get(self.guild.roles, id=self.bot.role_unregistered_id))

        # Remove busy status
        self.bot.users_busy.remove(user.id)

        # Print on the log channel
        log_channel = discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        embed = embeds.player(self.bot, auth)
        await log_channel.send(content=self.bot.quotes['cmdRegister_log'], embed=embed)

        # There can be permission errors if the user's role is higher in hierarchy than the bot
        try:
            await user.edit(nick=name)
        except Exception as e:
            pass

    def get_editplayer_buttons(self, player_to_edit):
        country_verified_emoji = "\u2714"
        if player_to_edit['country_verified'] == 0:
            country_verified_emoji = "\u274C"

        # Get the action to perform
        return [[
                    Button(style=ButtonStyle.grey, label="Change player name", custom_id=f"button_edit_player_changename_admin_{player_to_edit['id']}"),
                    Button(style=ButtonStyle.grey, label="Change auth", custom_id=f"button_edit_player_changeauth_admin_{player_to_edit['id']}"),
                    Button(style=ButtonStyle.grey, label="Change flag", emoji = flag.flagize(player_to_edit['country']), custom_id=f"button_edit_player_changeflag_admin_{player_to_edit['id']}")
                ],
                [
                    Button(style=ButtonStyle.grey, label="Verify country", emoji=country_verified_emoji, custom_id=f"button_edit_player_verify_country_admin_{player_to_edit['id']}"),
                    Button(style=ButtonStyle.red, label="Delete player", custom_id=f"button_edit_player_deleteplayer_admin_{player_to_edit['id']}")
                ]]


    @commands.command() 
    @check.is_guild_manager()
    async def editplayer(self, ctx, player_toedit):
        # Check if user is busy
        if ctx.author.id in self.bot.users_busy:
            await ctx.send('You are currently busy with another action with the bot, finish it and try again')
            return

        # Get the player info
        player_to_edit = self.bot.db.get_player(urt_auth=player_toedit)

        if not player_to_edit:
            await ctx.send(self.bot.quotes['cmdEditPlayer_admin_error_auth'])
            return

        # Get user's embed
        player_embed = embeds.player(self.bot, auth=player_to_edit['urt_auth'])
        editplayer_buttons = self.get_editplayer_buttons(player_to_edit)

        # Get the action to perform
        await ctx.send(embed = player_embed, components=editplayer_buttons)

    async def update_player_name(self, player_toedit, user, interaction): 
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Check your dms!")

        # Flag the user as busy
        self.bot.users_busy.append(user.id)

        def check(m):
                return m.author == user and m.guild == None

        # Wait for team name and check if the clan name is taken
        name_checked = False
        while not name_checked:
            await user.send(self.bot.quotes['cmdEditPlayer_update_name_prompt'])
            playername_msg = await self.bot.wait_for('message', check=check)
            playername = playername_msg.content.strip()

            # Cancel team edition
            if playername.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdEditPlayer_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if utils.emojis_in(playername_msg.content.strip()) or len(playername_msg.content.strip()) > 50:
                await user.send("Invalid entry, too long or includes emoji, try again.")
                continue

            # Check if ingame name is already taken 
            if self.bot.db.get_player(ingame_name=playername):
                await user.send(self.bot.quotes['cmdRegister_error_nametaken'])
            else:
                name_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.db.edit_player(player_toedit['id'], ingame_name=playername)
        ftw_client: FTWClient = self.bot.ftw
        await ftw_client.user_create_or_update(player_toedit['discord_id'], playername, player_toedit['urt_auth'])

        await user.send(self.bot.quotes['cmdEditPlayer_update_name_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEditPlayer_update_name_log'].format(oldname=player_toedit['ingame_name'], newname=playername))

        # There can be permission errors if the user's role is higher in hierarchy than the bot
        try:
            user_to_rename = discord.utils.get(self.guild.members, id=int(player_toedit['discord_id']))
            await user_to_rename.edit(nick=playername)
        except Exception as e:
            pass

    async def update_player_auth(self, player_toedit, user, interaction): 
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Check your dms!")

        # Flag the user as busy
        self.bot.users_busy.append(user.id)

        def check(m):
                return m.author == user and m.guild == None

        # Wait for team name and check if the clan name is taken
        auth_checked = False
        while not auth_checked:
            await user.send(self.bot.quotes['cmdEditPlayer_update_auth_prompt'])
            auth_msg = await self.bot.wait_for('message', check=check)
            auth = auth_msg.content.strip()

            # Cancel team edition
            if auth.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdEditPlayer_cancel'])
                # Remove busy status
                self.bot.users_busy.remove(user.id)
                return

            if utils.emojis_in(auth) or len(auth) > 50:
                await user.send("Invalid entry, too long or includes emoji, try again.")
                continue

            if not utils.check_auth(auth):
                await user.send(self.bot.quotes['cmdRegister_error_authdoesntexist'])
                continue

            # Check if auth is already taken 
            if self.bot.db.get_player(urt_auth=auth):
                await user.send(self.bot.quotes['cmdRegister_error_authalreadyreg'])
            else:
                auth_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.db.edit_player(player_toedit['id'], urt_auth=auth)
        self.bot.async_loop.create_task(update.roster(self.bot))

        ftw_client: FTWClient = self.bot.ftw
        await ftw_client.user_create_or_update(player_toedit['discord_id'], player_toedit['ingame_name'], auth)

        await user.send(self.bot.quotes['cmdEditPlayer_update_auth_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEditPlayer_update_auth_log'].format(playername=player_toedit['ingame_name'], oldauth=player_toedit['urt_auth'], newauth=auth))

    async def update_player_flag(self, player_toedit, user, interaction):
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content="Check your dms!")

        # Flag the user as busy
        self.bot.users_busy.append(user.id)

        def check(m):
                return m.author == user and m.guild == None

        # Wait for team flag and check if this is a flag emoji 
        oldflag = flag.flagize(player_toedit['country'])
        country_checked = False
        while not country_checked:
            await user.send(self.bot.quotes['cmdEditPlayer_update_flag_prompt_flag'])
            country_msg = await self.bot.wait_for('message', check=check)
            country = country_msg.content.strip()
            serialized_country = flag.dflagize(country)

            # Cancel
            if country.lower() == '!cancel':
                await user.send(self.bot.quotes['cmdEditPlayer_update_flag_cancel'])
                return

            if not self.bot.db.get_country(id=serialized_country):
                await user.send(self.bot.quotes['cmdRegister_error_country'])
            else:
                country_checked = True

                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.db.edit_player(player_toedit['id'], country=serialized_country)

        await user.send(self.bot.quotes['cmdEditPlayer_update_flag_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEditPlayer_update_flag_log'].format(playername=player_toedit['ingame_name'], oldflag=oldflag, newflag=country))

    async def delete_player(self, player_toedit, user, interaction):
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayerAdmin_intro'].format(playername=player_toedit['ingame_name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_deleteplayer_admin_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_deleteplayer_admin_no"),]])
        interaction_deleteplayeradmin = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_deleteplayer_admin_"))

        if interaction_deleteplayeradmin.component.id == 'button_deleteplayer_admin_no':
            await interaction_deleteplayeradmin.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayerAdmin_cancel'])
            return
        
        if interaction_deleteplayeradmin.component.id == 'button_deleteplayer_admin_yes':
            # Remove from db 
            self.bot.db.delete_player(player_toedit['id'])
            self.bot.db.delete_player_from_roster(player_toedit['id'])

            # Get the teams the player was captain of
            teams_owned = self.bot.db.get_teams_of_player(player_toedit['id'])

            for team_toedit in teams_owned:

                # Check if there are any players left on the team
                new_cap_id = self.bot.db.get_players_of_team(team_toedit['id'])[0]

                # Name new captain
                if new_cap_id:
                    self.bot.db.update_roster_status(RosterStatus.Captain, new_cap_id['player_id'], team_toedit['id'])
                    self.bot.db.edit_clan(team_toedit['tag'], captain=new_cap_id['player_id'])
                    ftw_client: FTWClient = self.bot.ftw
                    await ftw_client.team_add_user_or_update_role(team_toedit['ftw_team_id'], new_cap_id['discord_id'], UserTeamRole.leader)

                # Otherwise delete team
                else:
                    # Get channel and remove message
                    roster_channel = discord.utils.get(self.guild.channels, id=self.bot.channel_roster_id)
                    try:
                        roster_message = await roster_channel.fetch_message(team_toedit['roster_message_id'])
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
                    self.bot.db.delete_clan(team_toedit['tag'])

                    # Print on the log channel
                    log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                    await log_channel.send(self.bot.quotes['cmdDeleteClan_log'].format(teamname=team_toedit['name']))


            # Kick the deleted player
            # There can be permission errors if the user's role is higher in hierarchy than the bot
            try:
                user_to_kick = discord.utils.get(self.guild.members, id=int(player_toedit['discord_id']))
                # remove its roles
                for role in user_to_kick.roles:
                    user_to_kick.remove_roles(role)

                await user_to_kick.kick()
            except Exception as e:
                print(e)
                pass

            await interaction_deleteplayeradmin.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayerAdmin_prompt_success'])

            # Print on the log channel
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdDeletePlayerAdmin_prompt_log'].format(playername=player_toedit['ingame_name']))


    async def verify_country(self, player_toedit, user, interaction):
        await interaction.respond(type=6)

        status = "verified"
        verified = 1
        if player_toedit['country_verified'] == 1:
            status = "unverified"
            verified = 0

        self.bot.db.edit_player(player_toedit['id'], country_verified=verified)
        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEditPlayer_country_verified_success'].format(playername=player_toedit['ingame_name'], status=status))
        

def setup(bot):
    bot.add_cog(Account(bot))