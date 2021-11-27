import discord
from discord import channel
from discord.ext import commands, tasks
import cogs.common.utils as utils
import cogs.common.embeds as embeds
import cogs.common.update as update
import cogs.common.check as check
import cogs.common.dropmenus as dropmenus
import datetime
# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component, interaction

class ServerRequest(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.guilds[0]

    @commands.Cog.listener() 
    async def on_button_click(self, interaction):
        user = discord.utils.get(self.guild.members, id=interaction.user.id)
        # Get user info
        self.bot.cursor.execute("SELECT * FROM Users WHERE discord_id = %s;", (user.id,))
        user_info = self.bot.cursor.fetchone()

        if interaction.component.id.startswith("button_fixture_requestserver"):
            await self.request_server(interaction, user_info)

    # Request a server for a game
    async def request_server(self, interaction, user_info):
        # Get  feature  
        self.bot.cursor.execute("SELECT * FROM Fixtures WHERE channel_id=%s", (interaction.message.channel.id,))
        fixture_info = self.bot.cursor.fetchone()

        '''
        # Check if we are match day
        gamedate = datetime.date.fromisoformat(fixture_info['date'].split()[0])
        if gamedate != datetime.datetime.now().date():
            await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdPickBanInvitation_error_gamedate'])
            return
        '''

        # Make server location drop menu
        region_list = [
            ["East coast", "\U0001F1FA\U0001F1F8"],
            ["West coast", "\U0001F1FA\U0001F1F8"],
            ["UK", "\U0001F1EC\U0001F1E7"],
            ["France", "\U0001F1EB\U0001F1F7"],
            ["Germany", "\U0001F1E9\U0001F1EA"]
        ]
        server_region_dropmenu = dropmenus.server_regions(region_list)

        # Get server location
        await interaction.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdServerRequest_promptregion'], components=server_region_dropmenu)
        interaction_serverlocation = await self.bot.wait_for("select_option", check = lambda i: i.parent_component.id == "dropmenu_server_region" and i.message.channel.id == interaction.message.channel.id)
        server_location = region_list[int(interaction_serverlocation.component[0].value)]

        # TODO: Generate server
        server_ip = "serverip"
        server_pass = "serverpass"
        server_rcon = "serverrcon"

        await interaction_serverlocation.respond(type=InteractionType.ChannelMessageWithSource, content=self.bot.quotes['cmdServerRequest_success'].format(location=server_location[0], location_emoji=server_location[1], ip=server_ip, password=server_pass, rcon=server_rcon, username=user_info['ingame_name']))




def setup(bot):
    bot.add_cog(ServerRequest(bot))