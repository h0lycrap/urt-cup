import discord
from discord.ext import commands
import cogs.common.utils as utils
import cogs.common.embeds as embeds

# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption

class Account(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_raw_reaction_add(self, payload): # TODO: refactor with button
        if payload.message_id == self.bot.message_welcome_id and str(payload.emoji) == '\U0001F440':

            # Check if user is already registered
            self.bot.cursor.execute("SELECT urt_auth FROM Users WHERE discord_id = %s;", (payload.user_id,)) 
            if self.bot.cursor.fetchone():
                return

            user = discord.utils.get(self.guild.members, id=payload.user_id)
            await self.register(user)

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        if interaction.component.id == "button_register":

            user = discord.utils.get(self.guild.members, id=interaction.user.id)

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

def setup(bot):
    bot.add_cog(Account(bot))