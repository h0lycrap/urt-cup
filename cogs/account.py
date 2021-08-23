import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.check as check
import cogs.common.update as update

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

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
            self.bot.cursor.execute("SELECT urt_auth FROM Users WHERE discord_id = %s;", (interaction.user.id,)) 
            if self.bot.cursor.fetchone():
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

            self.bot.cursor.execute("SELECT * FROM Users WHERE id = %s;", (player_id,))
            player_to_edit = self.bot.cursor.fetchone()

            # Launch the action
            if interaction.component.id.startswith("button_edit_player_changename"):
                await self.update_player_name(player_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_player_changeauth"):
                await self.update_player_auth(player_to_edit, user, interaction)
            elif interaction.component.id.startswith("button_edit_player_delete"):
                await self.delete_player(player_to_edit, user, interaction)

            # Update the roster
            self.bot.async_loop.create_task(update.roster(self.bot))
        

    
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
            self.bot.cursor.execute("SELECT discord_id FROM Users WHERE urt_auth = %s", (auth,))   
            if self.bot.cursor.fetchone():
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
            self.bot.cursor.execute("SELECT discord_id FROM Users WHERE ingame_name = %s", (name,))   
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdRegister_error_nametaken'])
            else:
                name_checked = True

        # Wait for flag and check if this is a flag emoji 
        country_checked = False
        while not country_checked:
            await user.send(self.bot.quotes['cmdRegister_prompt_country'])
            country_msg = await self.bot.wait_for('message', check=check)
            country, country_checked = utils.check_flag_emoji(self.bot.cursor, country_msg.content.strip())

            if not country_checked:
                await user.send(self.bot.quotes['cmdRegister_error_country'])

        # Add user to DB and remove unregistered role
        self.bot.cursor.execute("INSERT INTO Users(discord_id, urt_auth, ingame_name, country) VALUES (%s, %s, %s, %s) ;", (user.id, auth, name, country))
        self.bot.conn.commit()
        await user.send(self.bot.quotes['cmdRegister_success'])
        await user.remove_roles(discord.utils.get(self.guild.roles, id=self.bot.role_unregistered_id))

        # Remove busy status
        self.bot.users_busy.remove(user.id)

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        embed = embeds.player(self.bot, auth)
        await log_channel.send(content=self.bot.quotes['cmdRegister_log'], embed=embed)

        # There can be permission errors if the user's role is higher in hierarchy than the bot
        try:
            await user.edit(nick=name)
        except Exception as e:
            pass

    @commands.command() 
    @check.is_guild_manager()
    async def editplayer(self, ctx, player_toedit):
        # Check if user is busy
        if ctx.author.id in self.bot.users_busy:
            await ctx.send('You are currently busy with another action with the bot, finish it and try again')
            return

        # Get the player info
        self.bot.cursor.execute("SELECT * FROM Users WHERE urt_auth=%s;", (player_toedit,))
        player_to_edit = self.bot.cursor.fetchone()

        if not player_to_edit:
            await ctx.send(self.bot.quotes['cmdEditPlayer_admin_error_auth'])
            return

        # Get user's embed
        player_embed = embeds.player(self.bot, auth=player_to_edit['urt_auth'])

        # Get the action to perform
        await ctx.send(embed = player_embed, components=[[
                                Button(style=ButtonStyle.grey, label="Change player name", custom_id=f"button_edit_player_changename_admin_{player_to_edit['id']}"),
                                Button(style=ButtonStyle.grey, label="Change auth", custom_id=f"button_edit_player_changeauth_admin_{player_to_edit['id']}")
                            ],
                            [
                                Button(style=ButtonStyle.red, label="Delete player", custom_id=f"button_edit_player_deleteplayer_admin_{player_to_edit['id']}")
                            ]])

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
            self.bot.cursor.execute("SELECT discord_id FROM Users WHERE ingame_name = %s", (playername,))   
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdRegister_error_nametaken'])
            else:
                name_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.cursor.execute("UPDATE Users SET ingame_name=%s WHERE id=%s", (playername, player_toedit['id']))
        self.bot.conn.commit()
        self.bot.async_loop.create_task(update.roster(self.bot))

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
            self.bot.cursor.execute("SELECT discord_id FROM Users WHERE urt_auth = %s", (auth,))   
            if self.bot.cursor.fetchone():
                await user.send(self.bot.quotes['cmdRegister_error_authalreadyreg'])
            else:
                auth_checked = True
                # Remove busy status
                self.bot.users_busy.remove(user.id)

        self.bot.cursor.execute("UPDATE Users SET urt_auth=%s WHERE id=%s", (auth, player_toedit['id']))
        self.bot.conn.commit()
        self.bot.async_loop.create_task(update.roster(self.bot))

        await user.send(self.bot.quotes['cmdEditPlayer_update_auth_success'])

        # Print on the log channel
        log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
        await log_channel.send(self.bot.quotes['cmdEditPlayer_update_auth_log'].format(playername=player_toedit['ingame_name'], oldauth=player_toedit['urt_auth'], newauth=auth))

    async def delete_player(self, player_toedit, user, interaction):
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayerAdmin_intro'].format(playername=player_toedit['ingame_name']), components=[[
                                    Button(style=ButtonStyle.green, label="Yes", custom_id="button_deleteplayer_admin_yes"),
                                    Button(style=ButtonStyle.red, label="No", custom_id="button_deleteplayer_admin_no"),]])
        interaction_deleteplayeradmin = await self.bot.wait_for("button_click", check = lambda i: i.user.id == user.id and i.component.id.startswith("button_deleteplayer_admin_"))

        if interaction_deleteplayeradmin.component.id == 'button_deleteplayer_admin_no':
            await interaction_deleteplayeradmin.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayerAdmin_cancel'])
            return
        
        if interaction_deleteplayeradmin.component.id == 'button_deleteplayer_admin_yes':
            # Remove from Users base 
            self.bot.cursor.execute("DELETE FROM Users WHERE id = %s;", (player_toedit['id'],))
            self.bot.conn.commit()

            # Remove from Roster 
            self.bot.cursor.execute("DELETE FROM Roster WHERE player_id = %s;", (player_toedit['id'],))
            self.bot.conn.commit()

            # Get the teams the player was captain of
            self.bot.cursor.execute("SELECT * FROM Teams WHERE captain = %s;", (player_toedit['id'],))
            teams_owned = self.bot.cursor.fetchall()

            for team_toedit in teams_owned:

                # Check if there are any players left on the team
                self.bot.cursor.execute("SELECT * FROM Roster WHERE team_id = %s;", (team_toedit['id'],))
                new_cap_id = self.bot.cursor.fetchone()

                # Name new captain
                if new_cap_id:
                    self.bot.cursor.execute("UPDATE Roster SET accepted=2 WHERE team_id = %s AND player_id=%s;", (team_toedit['id'], new_cap_id['player_id']))
                    self.bot.conn.commit()

                    self.bot.cursor.execute("UPDATE Teams SET captain=%s WHERE tag = %s ;", (new_cap_id['player_id'], team_toedit['tag']))
                    self.bot.conn.commit()

                # Otherwise delete team
                else:
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

                    # Print on the log channel
                    log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
                    await log_channel.send(self.bot.quotes['cmdDeleteClan_log'].format(teamname=team_toedit['name']))


            # Kick the deleted player
            # There can be permission errors if the user's role is higher in hierarchy than the bot
            try:
                user_to_kick = discord.utils.get(self.guild.members, id=int(player_toedit['discord_id']))
                await user_to_kick.kick()
            except Exception as e:
                print(e)
                pass

            await interaction_deleteplayeradmin.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdDeletePlayerAdmin_prompt_success'])

            # Print on the log channel
            log_channel =  discord.utils.get(self.guild.channels, id=self.bot.channel_log_id)
            await log_channel.send(self.bot.quotes['cmdDeletePlayerAdmin_prompt_log'].format(playername=player_toedit['ingame_name']))

        

def setup(bot):
    bot.add_cog(Account(bot))